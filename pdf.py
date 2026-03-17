import os
import sys
import json
import time
import logging
import pymupdf  # type: ignore
import re
import pytesseract  # type: ignore
from pdf2image import convert_from_path  # type: ignore
from models import (
    JSONResume,
    Basics,
    Work,
    Education,
    Skill,
    Project,
    Award,
    BasicsSection,
    WorkSection,
    EducationSection,
    SkillsSection,
    ProjectsSection,
    AwardsSection,
)  # type: ignore
from llm_utils import initialize_llm_provider, extract_json_from_response, get_model_for_task, ReasoningIntensity  # type: ignore
from pymupdf_rag import to_markdown  # type: ignore
from typing import List, Optional, Dict, Any
from prompt import (
    DEFAULT_MODEL,
    MODEL_PARAMETERS,
    MODEL_PROVIDER_MAPPING,
    GEMINI_API_KEY,
)  # type: ignore
from prompts.template_manager import TemplateManager  # type: ignore
from transform import transform_parsed_data  # type: ignore

logger = logging.getLogger(__name__)


class PDFHandler:

    def __init__(self):
        self.template_manager = TemplateManager()
        self.model_name = get_model_for_task(ReasoningIntensity.HIGH)
        self.provider: Any = None
        self._initialize_llm_provider()

    def _initialize_llm_provider(self):
        """Initialize the appropriate LLM provider based on the model."""
        self.provider = initialize_llm_provider(self.model_name)

    def extract_text_from_pdf(self, pdf_path: str) -> Optional[str]:
        try:
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")

            doc = pymupdf.open(pdf_path)
            pages = range(doc.page_count)
            resume_text = to_markdown(
                doc,
                pages=pages,
            )
            
            # OCR Fallback: If text is very short/empty, it's likely an image-based PDF
            if not resume_text or len(resume_text.strip()) < 50:
                logger.info(f"⚠️ Low text density ({len(resume_text) if resume_text else 0} chars). triggering OCR fallback...")
                resume_text = self._extract_text_with_ocr(pdf_path)

            logger.debug(
                f"Extracted text from PDF: {len(resume_text) if resume_text else 0} characters"
            )
            return resume_text
        except Exception as e:
            logger.error(f"An error occurred while reading the PDF: {e}")
            return None

    def _extract_text_with_ocr(self, pdf_path: str) -> str:
        """Helper to extract text using OCR for image-based PDFs."""
        try:
            images = convert_from_path(pdf_path)
            full_text = ""
            for i, image in enumerate(images):
                page_text = pytesseract.image_to_string(image)
                full_text += f"\n--- Page {i+1} ---\n{page_text}"
            return full_text
        except Exception as e:
            logger.error(f"OCR Extraction failed: {str(e)}")
            return ""

    def _call_llm_for_section(
        self, section_name: str, text_content: str, prompt: str, return_model=None
    ) -> Optional[Dict]:
        try:
            start_time = time.time()
            logger.debug(
                f"🔄 Extracting {section_name} section using {self.model_name}..."
            )

            model_params = MODEL_PARAMETERS.get(
                self.model_name, {"temperature": 0.1, "top_p": 0.9}
            )

            section_system_message = self.template_manager.render_template(
                "system_message", section_name_param=section_name
            )
            if not section_system_message:
                logger.error(
                    f"❌ Failed to render system message template for {section_name}"
                )
                return None

            chat_params = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": section_system_message},
                    {"role": "user", "content": prompt},
                ],
                "options": {
                    "stream": False,
                    "temperature": model_params["temperature"],
                    "top_p": model_params["top_p"],
                },
            }

            kwargs = {}
            if return_model:
                kwargs["format"] = return_model.model_json_schema()

            # Use the appropriate provider to make the API call
            response = self.provider.chat(**chat_params, **kwargs)

            response_text = response["message"]["content"]

            try:
                response_text = extract_json_from_response(response_text)
                json_start = response_text.find("{")
                json_end = response_text.rfind("}")
                if json_start != -1 and json_end != -1:
                    response_text = response_text[json_start : json_end + 1]
                parsed_data = json.loads(response_text, strict=False)
                logger.debug(f"✅ Successfully extracted {section_name} section")

                transformed_data = transform_parsed_data(parsed_data)
                end_time = time.time()
                total_time = end_time - start_time
                logger.debug(
                    f"⏱️ Total time for separate section extraction: {total_time:.2f} seconds"
                )

                return transformed_data
            except json.JSONDecodeError as e:
                logger.error(f"❌ Error parsing JSON for {section_name} section: {e}")
                logger.error(f"Raw response: {response_text}")
                return None

        except Exception as e:
            logger.error(f"❌ Error calling LLM for {section_name} section: {e}")
            return None

    def extract_basics_section(self, resume_text: str) -> Optional[Dict]:
        prompt = self.template_manager.render_template(
            "basics", text_content=resume_text
        )
        if not prompt:
            logger.error("❌ Failed to render basics template")
            return None
        return self._call_llm_for_section("basics", resume_text, prompt, BasicsSection)
    def extract_experience_section(self, text:str)->Optional[str]:
        # Normalize spaces and cases
        clean_text = re.sub(r'\s+', ' ', text).strip().lower()

        # Define multiple heading patterns
        experience_patterns = [
            r"(?:work\s+experience)",
            r"(?:professional\s+experience)",
            r"(?:experience)",
            r"(?:employment\s+history)",
            r"(?:career\s+history)"
        ]

        # Combine into one regex
        pattern = "|".join(experience_patterns)

        # Match heading and capture until next section (e.g., PROJECTS, EDUCATION, SKILLS, etc.)
        match = re.search(rf"({pattern})(.*?)(?=(education|project|skill|achievement|position|responsibility|$))",
                        clean_text, re.DOTALL)

        if match:
            return match.group(2).strip()
        else:
            print("⚠️ Experience section not found — fallback to LLM context detection")
            return ""
    def extract_work_section(self, resume_text: str) -> Optional[Dict]:
        """
        Extracts only the work/experience section from the given resume text using the
        LLM and the predefined 'work' template.

        Steps:
        1. Extract the experience section (by context headers like 'Experience', 'Work Experience', etc.)
        2. Render the extraction template with that text.
        3. Call the model to parse and return structured work data.
        """

        try:
            # Step 1: Extract only the experience section text
            experience_text = self.extract_experience_section(resume_text)
            print("Experience section::", experience_text)
            if not experience_text:
                logger.warning("⚠️ No experience section detected in resume text.")
                return None

            # Step 2: Render your 'work' template with the extracted experience text
            prompt = self.template_manager.render_template(
                "work",
                text_content=experience_text
            )
            if not prompt:
                logger.error("❌ Failed to render work extraction template.")
                return None

            # Step 3: Call the model to extract the structured experience JSON
            response = self._call_llm_for_section(
                "work",
                experience_text,
                prompt,
                WorkSection
            )

            if not response:
                logger.error("❌ No response from LLM for work section extraction.")
                return None

            logger.info("✅ Successfully extracted work section.")
            return response

        except Exception as e:
            logger.exception(f"🔥 Error extracting work section: {e}")
            return None

    def extract_education_section(self, resume_text: str) -> Optional[Dict]:
        prompt = self.template_manager.render_template(
            "education", text_content=resume_text
        )
        if not prompt:
            logger.error("❌ Failed to render education template")
            return None
        return self._call_llm_for_section(
            "education", resume_text, prompt, EducationSection
        )

    def extract_skills_section(self, resume_text: str) -> Optional[Dict]:
        prompt = self.template_manager.render_template(
            "skills", text_content=resume_text
        )
        if not prompt:
            logger.error("❌ Failed to render skills template")
            return None
        return self._call_llm_for_section("skills", resume_text, prompt, SkillsSection)

    def extract_projects_section(self, resume_text: str) -> Optional[Dict]:
        prompt = self.template_manager.render_template(
            "projects", text_content=resume_text
        )
        if not prompt:
            logger.error("❌ Failed to render projects template")
            return None
        return self._call_llm_for_section(
            "projects", resume_text, prompt, ProjectsSection
        )

    def extract_awards_section(self, resume_text: str) -> Optional[Dict]:
        prompt = self.template_manager.render_template(
            "awards", text_content=resume_text
        )
        if not prompt:
            logger.error("❌ Failed to render awards template")
            return None
        return self._call_llm_for_section("awards", resume_text, prompt, AwardsSection)

    def extract_json_from_text(self, resume_text: str) -> Optional[JSONResume]:
        try:
            return self._extract_all_sections_separately(resume_text)
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return None

    def extract_json_from_pdf(self, pdf_path: str) -> Optional[JSONResume]:
        try:
            logger.debug(f"📄 Extracting text from PDF: {pdf_path}")
            text_content = self.extract_text_from_pdf(pdf_path)

            if not text_content:
                logger.error("❌ Failed to extract text from PDF")
                return None

            logger.debug(
                f"✅ Successfully extracted {len(text_content)} characters from PDF"
            )

            logger.debug("🔄 Extracting all sections separately...")
            return self._extract_all_sections_separately(text_content)

        except Exception as e:
            logger.error(f"❌ Error during PDF to JSON extraction: {e}")
            return None

    def _extract_section_data(
        self, text_content: str, section_name: str, return_model=None
    ) -> Optional[Dict]:
        section_extractors = {
            "basics": self.extract_basics_section,
            "work": self.extract_work_section,
            "education": self.extract_education_section,
            "skills": self.extract_skills_section,
            "projects": self.extract_projects_section,
            "awards": self.extract_awards_section,
        }

        if section_name not in section_extractors:
            logger.error(f"❌ Invalid section name: {section_name}")
            logger.error(f"Valid sections: {list(section_extractors.keys())}")
            return None

        return section_extractors[section_name](text_content) # type: ignore

    def _extract_single_section(
        self, text_content: str, section_name: str, return_model=None
    ) -> Optional[Dict]:
        section_data = self._extract_section_data(
            text_content, section_name, return_model
        )
        if section_data:
            complete_resume = {
                "basics": None,
                "work": None,
                "volunteer": None,
                "education": None,
                "awards": None,
                "certificates": None,
                "publications": None,
                "skills": None,
                "languages": None,
                "interests": None,
                "references": None,
                "projects": None,
                "meta": None,
            }

            complete_resume.update(section_data)
            return complete_resume

        return None

    def _extract_all_sections_separately(
        self, text_content: str
    ) -> Optional[JSONResume]:
        start_time = time.time()

        sections = ["basics", "work", "education", "skills", "projects", "awards"]

        complete_resume = {
            "basics": None,
            "work": None,
            "volunteer": None,
            "education": None,
            "awards": None,
            "certificates": None,
            "publications": None,
            "skills": None,
            "languages": None,
            "interests": None,
            "references": None,
            "projects": None,
            "meta": None,
        }

        for section_name in sections:
            section_data = self._extract_section_data(text_content, section_name)

            if section_data:
                complete_resume.update(section_data)
                logger.debug(f"✅ Successfully extracted {section_name} section")
            else:
                logger.error(f"⚠️ Failed to extract {section_name} section")

        try:
            if complete_resume.get("basics") and isinstance(
                complete_resume["basics"], dict
            ):
                try:
                    complete_resume["basics"] = Basics(**complete_resume["basics"])
                except Exception as e:
                    logger.error(f"❌ Error creating Basics object: {e}")
                    complete_resume["basics"] = None

            json_resume = JSONResume(**complete_resume)

            end_time = time.time()
            total_time = end_time - start_time
            logger.info(
                f"⏱️ Total time for separate section extraction: {total_time:.2f} seconds"
            )
            return json_resume

        except Exception as e:
            logger.error(f"❌ Error during section extraction: {e}")
            return None

    def generate_evaluation_report(self, evaluation_data: Any, output_path: str):
        """Generates a premium, ultra-concise 1-2 page explainable PDF report."""
        try:
            import fitz # type: ignore
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            doc = fitz.open()
            page = doc.new_page()
            
            # Constants
            PAGE_HEIGHT = page.rect.height
            PAGE_WIDTH = page.rect.width
            MARGIN = 35.0
            BOTTOM_MARGIN = 45.0
            FONT_NORMAL, FONT_BOLD = "helv", "hebo"
            
            # Theme Colors
            C_PRIMARY = (0.05, 0.1, 0.3)
            C_SEC = (0.3, 0.5, 1.0)
            C_TEXT = (0.1, 0.1, 0.15)
            C_MUTED = (0.4, 0.4, 0.45)
            C_ERR = (0.7, 0.1, 0.1)
            C_OK = (0.05, 0.5, 0.25)
            
            class LayoutState:
                def __init__(self, p: Any):
                    self.pos_y = 90.0
                    self.current_page = p

            state = LayoutState(page)

            def ensure_space(h: float):
                if state.pos_y + h > PAGE_HEIGHT - BOTTOM_MARGIN:
                    state.current_page = doc.new_page()
                    state.pos_y = MARGIN + 10.0
                    return True
                return False

            def write_text(text: Any, font=FONT_NORMAL, size=9.0, color=C_TEXT, x=MARGIN, w=None, align=0, indent=0.0):
                if not text: return 0.0
                ensure_space(size + 2.0)
                width = (w if w else (PAGE_WIDTH - x - MARGIN)) - indent
                rect = fitz.Rect(x + indent, state.pos_y, x + indent + width, PAGE_HEIGHT - BOTTOM_MARGIN)
                clean_text = str(text)[:1000]
                h = state.current_page.insert_textbox(rect, clean_text, fontsize=size, fontname=font, color=color, align=align)
                if h < 0:
                    ensure_space(PAGE_HEIGHT)
                    rect = fitz.Rect(x + indent, state.pos_y, x + indent + width, PAGE_HEIGHT - BOTTOM_MARGIN)
                    h = state.current_page.insert_textbox(rect, clean_text, fontsize=size, fontname=font, color=color, align=align)
                if h > 0: state.pos_y += h + 2.0
                return h

            # 1. HEADER
            state.current_page.draw_rect(fitz.Rect(0, 0, PAGE_WIDTH, 70), fill=C_PRIMARY, stroke_opacity=0)
            state.current_page.insert_text(fitz.Point(MARGIN, 40), "IKSHA AI", fontsize=20, color=(1,1,1), fontname=FONT_BOLD)
            state.current_page.insert_text(fitz.Point(MARGIN, 55), "INTELLIGENCE REPORT", fontsize=8, color=(0.8,0.8,0.9))
            
            score_raw = evaluation_data.get('total_score', 0)
            score = int(score_raw) if str(score_raw).isdigit() else 0
            s_color = C_OK if score >= 70 else (C_SEC if score >= 40 else C_ERR)
            bx = PAGE_WIDTH - 65
            state.current_page.draw_circle(fitz.Point(bx, 35), 26, color=(1,1,1), fill=(1,1,1), width=0, overlay=True)
            state.current_page.insert_text(fitz.Point(bx - (10 if score >= 10 else 5), 45), str(score), fontsize=22, fontname=FONT_BOLD, color=s_color)
            state.current_page.insert_text(fitz.Point(bx - 12, 57), "SCORE", fontsize=5, fontname=FONT_BOLD, color=C_MUTED)

            # 2. SUMMARY
            state.pos_y = 85.0
            write_text("EXECUTIVE SUMMARY", font=FONT_BOLD, size=10.0, color=C_PRIMARY)
            summary_raw = evaluation_data.get('jd_fit_analysis', 'Analysis complete.')
            summary = str(summary_raw)
            write_text(summary[:400] + ("..." if len(summary) > 400 else ""), size=8.2)
            state.pos_y += 3.0

            # 3. METRICS
            ensure_space(15.0)
            state.current_page.draw_line(fitz.Point(MARGIN, state.pos_y + 10), fitz.Point(PAGE_WIDTH - MARGIN, state.pos_y + 10), color=C_PRIMARY, width=0.5)
            state.current_page.insert_text(fitz.Point(MARGIN, state.pos_y + 8), "ANALYSIS METRICS", fontsize=9, fontname=FONT_BOLD, color=C_PRIMARY)
            state.pos_y += 18.0
            
            scores = evaluation_data.get('scores', {})
            if scores:
                items = list(scores.items())
                cw = (PAGE_WIDTH - 2*MARGIN - 15) / 2
                for i in range(0, len(items), 2):
                    ensure_space(45.0)
                    row_y = state.pos_y
                    max_row_y = row_y
                    for j in range(min(2, len(items) - i)):
                        cat, val = items[i+j]
                        if not isinstance(val, dict): continue
                        xp = MARGIN + (j * (cw + 15))
                        name = str(cat).replace('_', ' ').title()
                        s = int(val.get('score', 0))
                        ms = int(val.get('max', 10))
                        ev = str(val.get('evidence', ''))[:100]
                        state.current_page.insert_text(fitz.Point(xp, state.pos_y + 8), name, fontsize=7.5, fontname=FONT_BOLD, color=C_PRIMARY)
                        state.current_page.insert_text(fitz.Point(xp + cw - 20, state.pos_y + 8), f"{s}/{ms}", fontsize=7.5, fontname=FONT_BOLD, color=s_color)
                        state.current_page.draw_rect(fitz.Rect(xp, state.pos_y + 11, xp + cw, state.pos_y + 12), fill=(0.95,0.95,0.95), stroke_opacity=0)
                        state.current_page.draw_rect(fitz.Rect(xp, state.pos_y + 11, xp + (cw * (s/ms if ms > 0 else 0)), state.pos_y + 12), fill=s_color, stroke_opacity=0)
                        rect = fitz.Rect(xp, state.pos_y + 14, xp + cw, state.pos_y + 40)
                        h = state.current_page.insert_textbox(rect, ev, fontsize=6.2, color=C_MUTED)
                        item_h = 14 + (h if h > 0 else 8)
                        state.pos_y += item_h
                        max_row_y = max(max_row_y, state.pos_y)
                    state.pos_y = max_row_y + 3.0

            # 4. SIGNALS
            ensure_space(50.0)
            state.current_page.draw_line(fitz.Point(MARGIN, state.pos_y + 10), fitz.Point(PAGE_WIDTH - MARGIN, state.pos_y + 10), color=C_PRIMARY, width=0.5)
            state.current_page.insert_text(fitz.Point(MARGIN, state.pos_y + 8), "INTELLIGENCE SIGNALS", fontsize=9, fontname=FONT_BOLD, color=C_PRIMARY)
            state.pos_y += 18.0
            
            str_list, imp_list = evaluation_data.get('key_strengths', [])[:4], evaluation_data.get('areas_for_improvement', [])[:4]
            cw = (PAGE_WIDTH - 2*MARGIN - 15) / 2
            start_y = state.pos_y
            state.current_page.insert_text(fitz.Point(MARGIN, start_y), "STRENGTHS", fontsize=7.5, fontname=FONT_BOLD, color=C_OK)
            state.current_page.insert_text(fitz.Point(MARGIN + cw + 15, start_y), "IMPROVEMENTS", fontsize=7.5, fontname=FONT_BOLD, color=C_ERR)
            state.pos_y = start_y + 9.0
            for i in range(max(len(str_list), len(imp_list))):
                ensure_space(35.0)
                row_y = state.pos_y
                cur_max = 0.0
                if i < len(str_list):
                    rect = fitz.Rect(MARGIN, row_y, MARGIN + cw, row_y + 30)
                    h = state.current_page.insert_textbox(rect, f"• {str_list[i]}", fontsize=6.8)
                    cur_max = max(cur_max, h)
                if i < len(imp_list):
                    rect = fitz.Rect(MARGIN + cw + 15, row_y, MARGIN + 2*cw + 15, row_y + 30)
                    h = state.current_page.insert_textbox(rect, f"• {imp_list[i]}", fontsize=6.8)
                    cur_max = max(cur_max, h)
                state.pos_y += (cur_max if cur_max > 0 else 8.0) + 2.0

            # 5. IDENTITY TRUST
            trust = evaluation_data.get('identity_trust', {})
            if trust:
                ensure_space(70.0)
                state.current_page.draw_line(fitz.Point(MARGIN, state.pos_y + 10), fitz.Point(PAGE_WIDTH - MARGIN, state.pos_y + 10), color=C_PRIMARY, width=0.5)
                state.current_page.insert_text(fitz.Point(MARGIN, state.pos_y + 8), "IDENTITY TRUST & AUTHENTICATION", fontsize=9, fontname=FONT_BOLD, color=C_PRIMARY)
                state.pos_y += 18.0
                
                risk_lvl = str(trust.get('fraud_risk_level', 'LOW')).upper()
                r_color = C_ERR if risk_lvl in ['HIGH', 'CRITICAL'] else (C_SEC if risk_lvl == 'MEDIUM' else C_OK)
                i_score = float(trust.get('identity_score', 0))
                write_text(f"Overall Trust: {i_score:.1f}/10  |  Fraud Risk: {risk_lvl}", size=8, font=FONT_BOLD, color=r_color)
                
                cw = (PAGE_WIDTH - 2*MARGIN - 20) / 3
                
                modules = [
                    (f"LinkedIn: {float(trust.get('linkedin',{}).get('linkedin_profile_score',0)):.1f}", MARGIN),
                    (f"GitHub: {float(trust.get('github',{}).get('github_activity_score',0)):.1f}", MARGIN + cw + 10),
                    (f"AI Prob: {float(trust.get('ai_resume_probability',0))*100:.0f}%", MARGIN + 2*cw + 20),
                    (f"Portfolio: {float(trust.get('portfolio',{}).get('portfolio_score',0)):.1f}", MARGIN),
                    (f"Consistent: {float(trust.get('resume_consistency',{}).get('timeline_consistency_score',0)):.1f}", MARGIN + cw + 10),
                    (f"Graph: {float(trust.get('social_graph_trust_score',0)):.1f}", MARGIN + 2*cw + 20)
                ]
                for i in range(0, len(modules), 3):
                    ensure_space(15.0)
                    row_y = state.pos_y
                    for j in range(min(3, len(modules) - i)):
                        lbl, xp = modules[i+j]
                        state.current_page.insert_text(fitz.Point(xp, row_y + 8), lbl, fontsize=7.2, color=C_TEXT)
                    state.pos_y += 12.0
                state.pos_y += 2.0
                
                flags = trust.get('fraud_flags', [])
                if flags:
                    ensure_space(15.0)
                    write_text("ALERTS:", font=FONT_BOLD, size=6.5, color=C_ERR)
                    for f in flags[:2]: write_text(f"! {f}", size=6.2, color=C_ERR, indent=3.0)

            # 6. MISMATCHES
            mismatches = evaluation_data.get('mismatch_reasons', [])
            if mismatches:
                state.pos_y += 5.0
                write_text("CRITICAL MISMATCHES", font=FONT_BOLD, size=9.0, color=C_ERR)
                for m in mismatches[:3]:
                    write_text(f"! {m}", size=7.5, indent=5.0)

            # Footer
            total_pages = len(doc)
            for i in range(total_pages):
                p = doc[i]
                p.draw_line(fitz.Point(35, PAGE_HEIGHT - 25), fitz.Point(PAGE_WIDTH - 35, PAGE_HEIGHT - 25), color=(0.9,0.9,0.9), width=0.5)
                p.insert_text(fitz.Point(35, PAGE_HEIGHT - 18), f"IKSHA AI | CONFIDENTIAL | {time.strftime('%Y-%m-%d')}", fontsize=5.5, color=C_MUTED)
                p.insert_text(fitz.Point(PAGE_WIDTH - 70, PAGE_HEIGHT - 18), f"Page {i+1} of {total_pages}", fontsize=5.5, color=C_MUTED)

            doc.save(output_path)
            doc.close()
            logger.info(f"✅ Premium report generated at: {output_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to generate PDF report: {e}")
            raise
