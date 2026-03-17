"use client";

import React, { useState, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, FileText, CheckCircle2, Loader2, Sparkles } from 'lucide-react';

interface GravityDropProps {
  onUpload: (file: File) => void;
  isProcessing: boolean;
}

export default function GravityDrop({ onUpload, isProcessing }: GravityDropProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type === 'application/pdf') {
      setFile(droppedFile);
      onUpload(droppedFile);
    }
  }, [onUpload]);

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      onUpload(selectedFile);
    }
  };

  const handleClick = () => {
    if (!isProcessing) {
      fileInputRef.current?.click();
    }
  };

  return (
    <div className="relative w-full max-w-xl mx-auto">
      <input 
        type="file" 
        ref={fileInputRef} 
        onChange={onFileChange} 
        className="hidden" 
        accept="application/pdf"
      />
      <motion.div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={handleClick}
        className={`relative group cursor-pointer overflow-hidden rounded-3xl border-2 border-dashed transition-all duration-500 min-h-[300px] flex flex-col items-center justify-center p-8 ${
          isDragOver 
            ? 'border-indigo-500 bg-indigo-500/10 scale-105' 
            : 'border-slate-700 bg-slate-900/50 hover:border-slate-500'
        }`}
        animate={{
          boxShadow: isDragOver ? '0 0 40px rgba(99, 102, 241, 0.4)' : '0 0 20px rgba(0,0,0,0)',
        }}
      >
        <AnimatePresence mode="wait">
          {!file ? (
            <motion.div
              key="empty"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="text-center"
            >
              <div className="mb-6 relative">
                <div className="absolute inset-0 bg-indigo-500/20 blur-3xl rounded-full" />
                <Upload className="w-16 h-16 text-indigo-400 mx-auto relative z-10 animate-bounce" />
              </div>
              <h3 className="text-2xl font-bold text-white mb-2">Drop your legacy.</h3>
              <p className="text-slate-400 mb-6">Enter the Antigravity Pipeline.</p>
              <div className="px-4 py-2 rounded-full border border-slate-700 bg-slate-800/50 text-xs text-slate-500 inline-block backdrop-blur-sm group-hover:bg-indigo-500/20 group-hover:text-indigo-300 transition-colors">
                Or click to browse PDFs
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="selected"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="text-center w-full"
            >
              <div className="relative inline-block mb-6">
                <FileText className="w-20 h-20 text-indigo-500 mx-auto" />
                {isProcessing && (
                  <div className="absolute inset-0 top-0 overflow-hidden rounded">
                    <div className="w-full h-1 bg-indigo-400 absolute animate-scan shadow-[0_0_10px_#6366f1]" />
                  </div>
                )}
                {!isProcessing && (
                  <CheckCircle2 className="w-8 h-8 text-emerald-500 absolute -bottom-2 -right-2 bg-slate-900 rounded-full" />
                )}
              </div>
              <p className="text-white font-medium text-lg truncate max-w-xs mx-auto mb-2">
                {file.name}
              </p>
              <div className="flex items-center justify-center gap-2 text-indigo-400 text-sm font-semibold">
                {isProcessing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Scanning Deep Reasoning...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    Extraction Ready
                  </>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
