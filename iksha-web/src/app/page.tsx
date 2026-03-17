"use client";

import React, { useState, useEffect } from 'react';
import ParticleBackground from '@/components/ParticleBackground';
import GravityDrop from '@/components/GravityDrop';
import TrustDashboard from '@/components/TrustDashboard';
import DeepReasoningAudit from '@/components/DeepReasoningAudit';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Shield, 
  Terminal, 
  Zap, 
  ChevronRight, 
  Activity, 
  LayoutDashboard, 
  SearchCode,
  LogOut
} from 'lucide-react';

type ViewState = 'landing' | 'analyzing' | 'main';
type SubView = 'dashboard' | 'audit';

export default function App() {
  const [view, setView] = useState<ViewState>('landing');
  const [subView, setSubView] = useState<SubView>('dashboard');
  const [isProcessing, setIsProcessing] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [resultData, setResultData] = useState<any>(null);

  const handleUpload = async (file: File) => {
    setIsProcessing(true);
    setLogs([]);
    setResultData(null);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch('http://localhost:8080/analyze', {
        method: 'POST',
        body: formData,
      });
      
      const { request_id } = await response.json();
      const eventSource = new EventSource(`http://localhost:8080/status/${request_id}`);
      
      eventSource.addEventListener('log', (event) => {
        setLogs(prev => [...prev, event.data]);
      });
      
      eventSource.addEventListener('complete', (event) => {
        const result = JSON.parse(event.data);
        setResultData(result.data);
        eventSource.close();
        
        setTimeout(() => {
          setView('main');
          setIsProcessing(false);
        }, 1200);
      });
      
      eventSource.onerror = () => {
        eventSource.close();
      };

    } catch (error) {
      console.error("Upload fail:", error);
      setIsProcessing(false);
    }
  };

  return (
    <main className="relative min-h-screen flex flex-col overflow-hidden bg-[#0F172A]">
      <ParticleBackground />
      
      {/* Dynamic Header */}
      <nav className="relative z-50 p-6 flex justify-between items-center border-b border-white/5 backdrop-blur-md bg-slate-950/20">
        <div className="flex items-center gap-2 cursor-pointer" onClick={() => setView('landing')}>
          <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center glow-primary">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-black tracking-tighter text-white">IKSHA <span className="text-indigo-500">AI</span></span>
        </div>
        
        <AnimatePresence>
          {view === 'main' && (
            <motion.div 
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center bg-white/5 border border-white/10 rounded-full p-1"
            >
              <button 
                onClick={() => setSubView('dashboard')}
                className={`flex items-center gap-2 px-6 py-2 rounded-full text-xs font-black uppercase tracking-widest transition-all ${
                  subView === 'dashboard' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20' : 'text-slate-400 hover:text-white'
                }`}
              >
                <LayoutDashboard className="w-4 h-4" /> Intelligence
              </button>
              <button 
                onClick={() => setSubView('audit')}
                className={`flex items-center gap-2 px-6 py-2 rounded-full text-xs font-black uppercase tracking-widest transition-all ${
                  subView === 'audit' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20' : 'text-slate-400 hover:text-white'
                }`}
              >
                <SearchCode className="w-4 h-4" /> Reasoning Audit
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="flex items-center gap-4">
          <div className="hidden lg:flex items-center gap-2 text-[10px] font-black uppercase tracking-tighter text-slate-500 border-r border-white/10 pr-4">
             <Activity className="w-3 h-3 text-emerald-400" /> System Integrity: Optimal
          </div>
          {view === 'main' ? (
            <button 
              onClick={() => {
                setView('landing');
                setIsProcessing(false);
              }}
              className="p-2 rounded-full bg-slate-800 text-slate-400 hover:text-white transition-colors border border-white/5"
            >
              <LogOut className="w-4 h-4" />
            </button>
          ) : (
            <button 
              onClick={async () => {
                setIsProcessing(true);
                setLogs([]);
                setResultData(null);
                try {
                  const response = await fetch('http://localhost:8080/demo', { method: 'POST' });
                  const { request_id } = await response.json();
                  const eventSource = new EventSource(`http://localhost:8080/status/${request_id}`);
                  
                  eventSource.addEventListener('log', (event) => {
                    setLogs(prev => [...prev, event.data]);
                  });
                  
                  eventSource.addEventListener('complete', (event) => {
                    const result = JSON.parse(event.data);
                    setResultData(result.data);
                    eventSource.close();
                    setTimeout(() => {
                      setView('main');
                      setIsProcessing(false);
                    }, 1200);
                  });
                  
                  eventSource.onerror = () => eventSource.close();
                } catch (error) {
                  console.error("Demo failed:", error);
                  setIsProcessing(false);
                }
              }}
              className="px-5 py-2 rounded-full border border-indigo-500/50 text-indigo-400 text-sm font-semibold hover:bg-indigo-500/10 transition-all flex items-center gap-2"
            >
              Enterprise Demo <ChevronRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </nav>

      <div className="flex flex-1 relative z-10 p-6 lg:p-8 overflow-hidden">
        <AnimatePresence mode="wait">
          {view === 'landing' && (
            <motion.div
              key="landing"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.05 }}
              className="w-full flex flex-col items-center justify-center space-y-12"
            >
              <div className="text-center">
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-8"
                >
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-bold mb-6">
                    <Zap className="w-3 h-3 fill-indigo-400" /> V1.0 - HYBRID INTELLIGENCE PIPELINE
                  </div>
                  <h1 className="text-6xl md:text-8xl font-black text-white tracking-tight mb-6">
                    Antigravity <br />
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-emerald-400">
                      Pipeline.
                    </span>
                  </h1>
                </motion.div>
                <GravityDrop onUpload={handleUpload} isProcessing={isProcessing} />
              </div>

              {/* Live Terminal Overlay when processing */}
              {isProcessing && (
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="w-full max-w-xl bg-black/60 backdrop-blur-xl border border-white/10 rounded-2xl p-6 font-mono text-xs"
                >
                  <div className="flex items-center gap-2 text-indigo-400 mb-4 pb-2 border-b border-white/5 uppercase tracking-widest font-black">
                    <Terminal className="w-3 h-3" /> Runtime_Logs
                  </div>
                  <div className="space-y-2 h-32 overflow-y-auto thin-scrollbar">
                    {logs.map((log, i) => (
                      <div key={i} className="flex gap-4">
                        <span className="text-slate-600">{i+1}.</span>
                        <span className={log?.includes('Complete') ? 'text-emerald-400' : 'text-slate-300'}>{log}</span>
                      </div>
                    ))}
                    <div className="w-1.5 h-3 bg-indigo-500 animate-pulse inline-block" />
                  </div>
                </motion.div>
              )}
            </motion.div>
          )}

          {view === 'main' && (
            <motion.div
              key="main"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="w-full h-[calc(100vh-160px)]"
            >
              {subView === 'dashboard' ? (
                <TrustDashboard data={resultData} />
              ) : (
                <DeepReasoningAudit data={resultData} />
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Footer Decoration */}
      <div className="absolute bottom-0 left-0 right-0 h-96 bg-gradient-to-t from-indigo-500/10 via-transparent to-transparent pointer-events-none z-0" />
    </main>
  );
}
