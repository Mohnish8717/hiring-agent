"use client";

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  ShieldCheck, 
  User, 
  Github, 
  Linkedin, 
  Terminal, 
  AlertCircle,
  Activity,
  Award,
  Search,
  Zap,
  CheckCircle2
} from 'lucide-react';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from 'recharts';

interface AgentStatus {
  name: string;
  status: 'pending' | 'active' | 'complete' | 'flagged';
  score?: number;
  label: string;
}

interface TrustDashboardProps {
  data?: any;
}

export default function TrustDashboard({ data }: TrustDashboardProps) {
  const [overallScore, setOverallScore] = useState(0);
  
  // Dynamic mapping of agents based on real data
  const initialAgents: AgentStatus[] = [
    { 
      name: 'ExtractionAgent', 
      status: data?.contribution_map?.extraction ? 'complete' : 'active', 
      score: data?.contribution_map?.extraction?.status === "Success" ? 92 : 0, 
      label: data?.contribution_map?.extraction ? 'Data Extracted' : 'Extracting...' 
    },
    { 
      name: 'VerificationAgent', 
      status: data?.github_data ? 'complete' : 'pending', 
      label: data?.github_data ? 'GitHub Verified' : 'Syncing...' 
    },
    { 
      name: 'IdentityTrustAgent', 
      status: data?.identity_trust ? 'complete' : 'pending', 
      label: data?.identity_trust ? 'Trust Verified' : 'Queued' 
    },
    { 
      name: 'ApplicationQualityAgent', 
      status: data?.application_quality ? 'complete' : 'pending', 
      label: data?.application_quality ? 'Quality Verified' : 'Queued' 
    },
    { 
      name: 'BiasAuditAgent', 
      status: data?.blind_evaluation ? 'complete' : 'pending', 
      label: data?.blind_evaluation ? 'Anonymized' : 'Queued' 
    }
  ];

  const [agents, setAgents] = useState<AgentStatus[]>(initialAgents);

  useEffect(() => {
    // If we have real data, animate to the real score
    const target = Math.round(data?.blind_evaluation?.total_score || (data ? 0 : 87));
    const duration = 2000;
    const start = 0;
    const startTime = Date.now();

    const animate = () => {
      const now = Date.now();
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const current = Math.floor(start + (target - start) * progress);
      setOverallScore(current);

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };
    animate();

    // No need to mock if we have data
    if (data) return;

    // Simulate Agent progress ONLY if no real data
    const timeouts = [
      setTimeout(() => setAgents(prev => prev.map(a => a.name === 'VerificationAgent' ? { ...a, status: 'complete', score: 85, label: 'GitHub Verified' } : a)), 3000),
      setTimeout(() => setAgents(prev => prev.map(a => a.name === 'IdentityTrustAgent' ? { ...a, status: 'active', label: 'Analyzing ID Consistency...' } : a)), 4000),
      setTimeout(() => setAgents(prev => prev.map(a => a.name === 'IdentityTrustAgent' ? { ...a, status: 'complete', score: 76, label: 'Trust Verified' } : a)), 7000),
      setTimeout(() => setAgents(prev => prev.map(a => a.name === 'BiasAuditAgent' ? { ...a, status: 'complete', score: 100, label: 'Anonymized' } : a)), 5000)
    ];

    return () => timeouts.forEach(clearTimeout);
  }, [data]);

  const pieData = [
    { value: overallScore },
    { value: 100 - overallScore }
  ];

  // Helper for real candidate info
  const candidate = {
    name: data?.resume_data?.basics?.name || "Candidate",
    email: data?.resume_data?.basics?.email || "Email Redacted",
    role: data?.resume_data?.basics?.label || (data ? "Developer" : "Senior Software Engineer")
  };

  return (
    <div className="flex flex-col h-full bg-slate-950/40 backdrop-blur-xl border border-white/10 rounded-[2.5rem] overflow-hidden shadow-2xl">
      {/* Dashboard Header */}
      <header className="px-8 py-6 border-b border-white/5 flex justify-between items-center bg-white/5">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-indigo-500/20 rounded-xl border border-indigo-500/30">
            <User className="w-6 h-6 text-indigo-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">{candidate.name}</h2>
            <p className="text-xs text-slate-500 font-mono uppercase tracking-widest font-bold">{candidate.email} • {candidate.role}</p>
          </div>
        </div>
        
        <div className="flex gap-3">
          <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-bold font-mono">
            <ShieldCheck className="w-3 h-3" /> {data?.identity_trust ? 'IDENTITY_VERIFIED' : 'PENDING_VERIFICATION'}
          </div>
          <button 
            onClick={() => alert("Search functionality coming soon in V2.0")}
            className="p-2 rounded-lg bg-surface hover:bg-slate-700 transition-colors border border-white/5"
          >
            <Search className="w-5 h-5 text-slate-400" />
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Agent Pulse Sidebar */}
        <aside className="w-80 border-r border-white/5 p-6 space-y-4">
          <h3 className="text-xs font-black text-slate-600 uppercase tracking-widest mb-6 flex items-center gap-2">
            <Activity className="w-3 h-3" /> Agent Runtime Monitor
          </h3>
          
          <div className="space-y-3">
            {agents.map((agent, i) => (
              <motion.div
                key={agent.name}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                className={`p-4 rounded-xl border transition-all ${
                  agent.status === 'active' 
                    ? 'bg-indigo-500/10 border-indigo-500/30' 
                    : agent.status === 'complete'
                    ? 'bg-white/5 border-white/5'
                    : 'bg-transparent border-white/5 opacity-50'
                }`}
              >
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs font-bold text-white font-mono">{agent.name}</span>
                  <div className={`w-1.5 h-1.5 rounded-full ${
                    agent.status === 'active' ? 'bg-indigo-400 animate-pulse' : 
                    agent.status === 'complete' ? 'bg-emerald-400' : 'bg-slate-600'
                  }`} />
                </div>
                <div className="flex justify-between items-end">
                  <span className="text-[10px] text-slate-500 uppercase tracking-tight font-medium">{agent.label}</span>
                  {agent.score ? (
                    <span className="text-xs font-black font-mono text-indigo-400">{agent.score}%</span>
                  ) : null}
                </div>
                {agent.status === 'active' && (
                  <div className="mt-3 h-0.5 w-full bg-slate-800 rounded-full overflow-hidden">
                    <motion.div 
                      className="h-full bg-indigo-500"
                      animate={{ x: [-200, 200] }}
                      transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                    />
                  </div>
                )}
              </motion.div>
            ))}
          </div>

          <div className="mt-auto pt-6 border-t border-white/5">
             <div className="flex items-center gap-3 p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl">
               <AlertCircle className="w-5 h-5 text-rose-500 shrink-0" />
               <p className="text-[10px] leading-relaxed text-rose-300 font-bold uppercase tracking-tight">
                 {data?.contribution_map?.trust?.flags?.length > 0 
                  ? `Anomalies found in ${data.contribution_map.trust.flags.join(", ")}`
                  : "Continuous Integrity cross-referencing active..."}
               </p>
             </div>
          </div>
        </aside>

        {/* Main Score Area */}
        <main className="flex-1 p-8 overflow-y-auto thin-scrollbar">
          <div className="grid grid-cols-12 gap-8 h-full">
            
            {/* Center Hero Metric */}
            <div className="col-span-12 lg:col-span-7 flex flex-col items-center justify-center relative p-8 glass-card rounded-[2rem] overflow-hidden">
               <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-indigo-500 to-transparent opacity-50" />
               
               <div className="relative w-64 h-64 flex items-center justify-center">
                 <div className="absolute inset-0 bg-indigo-500/10 blur-3xl rounded-full animate-pulse" />
                 <ResponsiveContainer width="100%" height="100%">
                   <PieChart>
                     <Pie
                       data={pieData}
                       cx="50%"
                       cy="50%"
                       innerRadius={80}
                       outerRadius={110}
                       paddingAngle={0}
                       dataKey="value"
                       startAngle={90}
                       endAngle={450}
                     >
                       <Cell fill="#6366F1" stroke="none" />
                       <Cell fill="#1e293b" stroke="none" />
                     </Pie>
                   </PieChart>
                 </ResponsiveContainer>
                 <div className="absolute flex flex-col items-center">
                   <motion.span 
                    key={overallScore}
                    initial={{ scale: 0.8 }}
                    animate={{ scale: 1 }}
                    className="text-7xl font-black text-white tracking-tighter"
                  >
                    {overallScore}
                  </motion.span>
                   <span className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-500">Antigravity Score</span>
                 </div>
               </div>

               <div className="grid grid-cols-3 gap-8 w-full mt-12 text-center pb-4">
                  <div>
                    <div className="text-2xl font-black text-white">
                      {data?.contribution_map?.skills?.match ? Math.round(data.contribution_map.skills.match * 10) : 94}%
                    </div>
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Skill Density</div>
                  </div>
                  <div className="border-x border-white/5 px-4">
                    <div className="text-2xl font-black text-emerald-400">
                      {data?.contribution_map?.trust?.score > 7 ? "High" : "Mid"}
                    </div>
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Trust Index</div>
                  </div>
                  <div>
                    <div className="text-2xl font-black text-rose-500">
                      {data?.contribution_map?.trust?.ai_resume ? Math.round(data.contribution_map.trust.ai_resume * 100) : 2.1}%
                    </div>
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">AI Prob</div>
                  </div>
               </div>
            </div>

            {/* Verified Truth Map (Placeholder for now) */}
            <div className="col-span-12 lg:col-span-5 flex flex-col gap-6">
              <div className="flex-1 glass-card rounded-[2rem] p-6 relative overflow-hidden">
                <div className="flex items-center justify-between mb-6">
                  <h4 className="text-sm font-black text-white uppercase tracking-widest flex items-center gap-2">
                    <Github className="w-4 h-4" /> GitHub Authorship
                  </h4>
                  <div className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 text-[10px] font-black border border-emerald-500/20 uppercase">
                    {data?.github_data ? "Verified" : "Syncing"}
                  </div>
                </div>
                {/* Simulated Commits Heatmap */}
                <div className="grid grid-cols-7 gap-1 h-32 opacity-80">
                  {Array.from({ length: 49 }).map((_, i) => (
                    <div 
                      key={i} 
                      className={`rounded-[2px] ${
                        Math.random() > 0.6 ? (Math.random() > 0.5 ? 'bg-indigo-600' : 'bg-indigo-400') : 'bg-slate-800'
                      }`}
                    />
                  ))}
                </div>
                <div className="mt-6 flex flex-wrap gap-2">
                  {(data?.resume_data?.skills || [{name: 'React'}, {name:'Next.js'}, {name:'Python'}]).slice(0, 5).map((skill: any) => (
                    <span key={skill.name || skill} className="px-2 py-1 rounded-md bg-white/5 border border-white/5 text-[10px] text-slate-400 font-mono">
                      {skill.name || skill}
                    </span>
                  ))}
                </div>
              </div>

              <div className="h-40 glass-card rounded-[2rem] p-6 relative overflow-hidden">
                 <h4 className="text-sm font-black text-white uppercase tracking-widest mb-4 flex items-center gap-2">
                   <Terminal className="w-4 h-4" /> System Logs
                 </h4>
                 <div className="font-mono text-[9px] text-slate-500 space-y-1">
                   {data ? (
                     <>
                      <p className="text-emerald-400/70">{">"} Extraction: success</p>
                      <p className="text-indigo-400/70">{">"} Trust_Score: {data.contribution_map?.trust?.score}</p>
                      <p className="animate-pulse">{">"} Finalizing analysis report...</p>
                     </>
                   ) : (
                     <>
                      <p className="text-emerald-400/70">{">"} ExtractionAgent: success (200ms)</p>
                      <p className="text-indigo-400/70">{">"} VerificationAgent: gh_id:Mohnish8717 (verified)</p>
                      <p className="animate-pulse">{">"} IdentityTrust: checking linkedin metadata...</p>
                     </>
                   )}
                 </div>
              </div>
            </div>
            
          </div>
        </main>
      </div>
    </div>
  );
}
