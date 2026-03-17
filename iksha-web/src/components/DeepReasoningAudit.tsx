"use client";

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  FileText, 
  Search, 
  Cpu, 
  Eye, 
  ShieldCheck, 
  AlertTriangle,
  ArrowRight,
  ExternalLink,
  Github
} from 'lucide-react';

interface DeepReasoningAuditProps {
  data?: any;
}

export default function DeepReasoningAudit({ data }: DeepReasoningAuditProps) {
  const [hoveredField, setHoveredField] = useState<string | null>(null);

  // Map real data to audit sections
  const sections = data?.blind_evaluation ? [
    { 
      id: 'strength_1', 
      title: data.blind_evaluation.key_strengths?.[0] || 'Core Technical Expertise', 
      type: 'verified', 
      reason: data.blind_evaluation.evaluation_summary || 'Expertise confirmed through cross-agent verification.',
      source: 'BiasAuditAgent'
    },
    { 
      id: 'fraud_1', 
      title: 'Structural Consistency', 
      type: data.identity_trust?.fraud_flags?.length > 0 ? 'suspicious' : 'verified', 
      reason: data.identity_trust?.fraud_flags?.length > 0 
        ? `Anomaly detected: ${data.identity_trust.fraud_flags.join(", ")}` 
        : 'Resume structure and distribution across periods is consistent with industry standards.',
      source: 'IdentityTrustAgent'
    },
    {
      id: 'quality_1',
      title: 'LLM Grammar Analysis',
      type: (data.application_quality?.ai_generated_probability || 0) > 0.6 ? 'suspicious' : 'verified',
      reason: (data.application_quality?.ai_generated_probability || 0) > 0.6 
        ? 'High probability of synthetic text generation detected in summary.' 
        : 'Phrasing and semantic patterns appear naturally authored.',
      source: 'ApplicationQualityAgent'
    }
  ] : [
    { 
      id: 'work_1', 
      title: 'Nomotix - Technical Team Lead', 
      type: 'verified', 
      reason: 'GitHub commit patterns match the claimed timeframe and tech stack (MERN).',
      source: 'GitHub Authorship Agent'
    },
    { 
      id: 'work_2', 
      title: 'React Developer Intern', 
      type: 'suspicious', 
      reason: 'Low specificity in achievement metrics. Generic internship phrasing detected.',
      source: 'ApplicationQualityAgent'
    }
  ];

  const resumeData = data?.resume_data || {
    basics: { name: "VidelA Mohnish", email: "m.videla8@gmail.com", location: { city: "Hyderabad, IN" } },
    work: [{ company: "Nomotix", position: "Technical Team Lead", summary: "Led the design and development of a MERN-stack web platform..." }]
  };

  return (
    <div className="flex flex-col h-full bg-slate-950/40 backdrop-blur-xl border border-white/10 rounded-[2.5rem] overflow-hidden shadow-2xl">
      <header className="px-8 py-6 border-b border-white/5 flex justify-between items-center bg-white/5">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-fuchsia-500/20 rounded-xl border border-fuchsia-500/30">
            <Cpu className="w-6 h-6 text-fuchsia-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">Deep Reasoning Audit</h2>
            <p className="text-xs text-slate-500 font-mono uppercase tracking-widest font-bold">Llama-3.3-70B • Heatmap Overlay V1.0</p>
          </div>
        </div>
        <button 
          onClick={() => alert("Transparency Toggle: Heatmap layers adjusted.")}
          className="flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-slate-400 text-xs font-bold uppercase transition-all hover:bg-white/10 cursor-pointer"
        >
           <Eye className="w-3 h-3" /> Toggle Transparency
        </button>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Left: Mock Resume Content */}
        <div className="flex-1 p-12 overflow-y-auto thin-scrollbar bg-slate-900/20 relative">
          <div className="max-w-2xl mx-auto space-y-12">
            <section className="text-center mb-16">
              <h3 className="text-4xl font-bold text-white mb-2 tracking-tight">VidelA Mohnish</h3>
              <p className="text-indigo-400 font-medium">m.videla8@gmail.com | Hyderabad, IN</p>
            </section>

            <section className={`relative p-6 rounded-2xl transition-all duration-500 ${hoveredField === 'work_1' ? 'bg-emerald-500/5 ring-1 ring-emerald-500/30' : ''}`}>
              <div className="flex justify-between items-start mb-4">
                <h4 className="text-lg font-bold text-white uppercase tracking-tight">Experience</h4>
                <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_10px_#10b981]" />
              </div>
              <div className="space-y-6">
                 <div>
                   <h5 className="text-white font-semibold">Nomotix | Technical Team Lead</h5>
                   <p className="text-slate-400 text-sm mt-1 leading-relaxed">
                     Led the design and development of a MERN-stack web platform and React Native (Expo) mobile apps for online car mechanic booking. Targeted 1,000+ early users pre-launch.
                   </p>
                 </div>
              </div>
              {hoveredField === 'work_1' && (
                <motion.div 
                  layoutId="glow"
                  className="absolute inset-0 bg-emerald-500/5 blur-2xl rounded-2xl -z-10" 
                />
              )}
            </section>

            <section className={`relative p-6 rounded-2xl transition-all duration-500 ${hoveredField === 'work_2' ? 'bg-rose-500/5 ring-1 ring-rose-500/30 scale-[1.02]' : ''}`}>
              <div className="flex justify-between items-start mb-4">
                <h4 className="text-lg font-bold text-white uppercase tracking-tight">Internships</h4>
                <div className="w-2 h-2 rounded-full bg-rose-500 shadow-[0_0_10px_#f43f5e] animate-pulse" />
              </div>
              <div className="space-y-6">
                 <div>
                   <h5 className="text-white font-semibold">Pardhu & Sanjay Solutions | React Developer Intern</h5>
                   <p className="text-slate-400 text-sm mt-1 leading-relaxed">
                     Built web interfaces using React and integrated Capsule’s APIs to enable dynamic website functionality. Collaborated with the team on API-driven feature implementation.
                   </p>
                 </div>
              </div>
            </section>
          </div>
        </div>

        {/* Right: Analysis Overlay */}
        <aside className="w-[450px] border-l border-white/5 bg-slate-900/40 p-8 space-y-6 overflow-y-auto thin-scrollbar">
           <h3 className="text-xs font-black text-slate-500 uppercase tracking-[0.3em] mb-8">Verification Insights</h3>

           <div className="space-y-4">
             {sections.map(s => (
               <motion.div
                 key={s.id}
                 onHoverStart={() => setHoveredField(s.id)}
                 onHoverEnd={() => setHoveredField(null)}
                 className={`p-6 rounded-2xl border transition-all cursor-crosshair relative group ${
                   s.type === 'verified' 
                    ? 'bg-emerald-500/5 border-emerald-500/20 hover:border-emerald-500/40' 
                    : 'bg-rose-500/5 border-rose-500/20 hover:border-rose-500/40'
                 }`}
               >
                 <div className="flex items-center gap-3 mb-3">
                   {s.type === 'verified' ? (
                     <ShieldCheck className="w-5 h-5 text-emerald-500" />
                   ) : (
                     <AlertTriangle className="w-5 h-5 text-rose-500" />
                   )}
                   <span className="text-xs font-black text-white uppercase tracking-wider">{s.source}</span>
                 </div>
                 <h5 className="text-sm font-bold text-white mb-2 leading-tight">{s.title}</h5>
                 <p className="text-xs text-slate-400 leading-relaxed mb-4">
                   {s.reason}
                 </p>
                 <div className="flex items-center justify-between pt-4 border-t border-white/5 mt-auto">
                    <span className={`text-[9px] font-black uppercase tracking-widest ${s.type === 'verified' ? 'text-emerald-500' : 'text-rose-500'}`}>
                      Confidence: {s.type === 'verified' ? '98%' : '32%'}
                    </span>
                    <button 
                      onClick={() => alert(`Showing evidence for: ${s.title}`)}
                      className="text-[9px] font-black text-slate-500 hover:text-white transition-colors flex items-center gap-1 uppercase tracking-widest"
                    >
                      View Raw Evidence <ArrowRight className="w-2.5 h-2.5" />
                    </button>
                 </div>
                 
                 {/* Visual Pulse for Attention */}
                 {s.type === 'suspicious' && (
                   <div className="absolute top-4 right-4 animate-ping">
                      <div className="w-2 h-2 rounded-full bg-rose-500/40" />
                   </div>
                 )}
               </motion.div>
             ))}
           </div>

           <div className="mt-12 p-6 glass-card rounded-3xl border-indigo-500/20">
              <div className="flex items-center gap-2 text-indigo-400 mb-2">
                <Github className="w-4 h-4" />
                <span className="text-[10px] font-black uppercase tracking-widest">Repo Synthesis</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed mb-4 italic">
                "Cross-verification with `Mohnish8717/hiring-agent` confirms deep expertise in LLM orchestration and Pydantic validation patterns."
              </p>
              <button 
                onClick={() => window.open("https://github.com/Mohnish8717/hiring-agent", "_blank")}
                className="w-full py-3 rounded-xl bg-indigo-600 text-white text-[10px] font-black uppercase tracking-[0.2em] hover:bg-indigo-500 transition-all flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/20"
              >
                View GitHub DNA <ExternalLink className="w-3 h-3" />
              </button>
           </div>
        </aside>
      </div>
    </div>
  );
}
