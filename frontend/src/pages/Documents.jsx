import React, { useState, useRef, useEffect } from 'react';
import {
  FileText,
  Upload,
  Trash2,
  Sparkles,
  Send,
  HelpCircle,
  FileCheck,
  Search,
  BookOpen,
  ArrowRight,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import * as api from '../services/api';
import EmptyState from '../components/EmptyState';
import LoadingSpinner from '../components/LoadingSpinner';

export default function Documents() {
  const { data, uploadDoc, deleteDoc, loadDocuments } = useApp();
  const fileInputRef = useRef(null);

  const [selectedDocId, setSelectedDocId] = useState('');
  const [qaQuery, setQaQuery] = useState('');
  const [qaAnswer, setQaAnswer] = useState('');
  const [isAsking, setIsAsking] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [uploadSuccess, setUploadSuccess] = useState('');

  // Refresh user documents on mount
  useEffect(() => {
    if (typeof loadDocuments === 'function') {
      loadDocuments();
    }
  }, []);

  const documents = data?.documents || [];
  const selectedDoc = documents.find((d) => String(d.id) === String(selectedDocId)) || documents[0];

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate supported formats
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!['.pdf', '.txt', '.docx'].includes(ext)) {
      setUploadError('Unsupported file type. Please upload PDF, TXT, or DOCX.');
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    try {
      setIsUploading(true);
      setUploadError('');
      setUploadSuccess('');
      const res = await uploadDoc(file);
      setUploadSuccess(`Document "${file.name}" uploaded and indexed successfully.`);
      setTimeout(() => setUploadSuccess(''), 4000);

      // Refresh documents immediately so new document appears without page refresh
      if (typeof loadDocuments === 'function') {
        const freshDocs = await loadDocuments();
        if (freshDocs && freshDocs.length > 0) {
          const createdId = res?.document?.id || res?.id;
          const matching = freshDocs.find((d) => String(d.id) === String(createdId)) || freshDocs[0];
          if (matching) setSelectedDocId(matching.id);
        }
      }
    } catch (err) {
      setUploadError(err.message || 'File upload failed');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDelete = async (docId, docName) => {
    if (!window.confirm(`Are you sure you want to delete "${docName || 'this document'}"?`)) {
      return;
    }
    try {
      await deleteDoc(docId);
      if (typeof loadDocuments === 'function') {
        await loadDocuments();
      }
      if (String(selectedDocId) === String(docId)) {
        setSelectedDocId('');
      }
    } catch (err) {
      setUploadError(err.message || 'Failed to delete document');
    }
  };

  const handleAskQuestion = async (customQuery) => {
    const q = customQuery || qaQuery;
    const docToQuery = selectedDoc?.id;
    if (!q.trim() || isAsking) return;

    try {
      setIsAsking(true);
      setQaAnswer('');
      const res = await api.askDocumentQA(docToQuery, q);
      setQaAnswer(res.answer || "I couldn't find that information in your uploaded documents.");
    } catch (err) {
      setQaAnswer(`⚠️ Error querying document: ${err.message}`);
    } finally {
      setIsAsking(false);
    }
  };

  const ragPrompts = [
    'Summarize this document.',
    'What are the important topics covered?',
    'Create 5 practice exam questions from this text.',
    'Explain the key formulas or algorithms in this document.'
  ];

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm">
        <div>
          <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <FileText className="w-5 h-5 text-indigo-600" />
            Documents & Document AI
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Upload course materials (PDF, TXT, DOCX) and perform AI context retrieval and question answering.
          </p>
        </div>

        {/* Hidden File Input for both buttons */}
        <input
          ref={fileInputRef}
          id="document-upload-input"
          type="file"
          accept=".pdf,.txt,.docx"
          onChange={handleFileUpload}
          disabled={isUploading}
          className="hidden"
        />

        {/* Header Upload Button */}
        <button
          type="button"
          id="upload-document-header-btn"
          onClick={() => fileInputRef.current?.click()}
          disabled={isUploading}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold cursor-pointer shadow-md shadow-indigo-600/20 active:scale-95 transition disabled:opacity-50"
        >
          <Upload className="w-4 h-4" />
          <span>{isUploading ? 'Uploading & Indexing...' : 'Upload Document'}</span>
        </button>
      </div>

      {uploadSuccess && (
        <div className="flex items-center gap-2 p-3 bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-900 rounded-xl text-xs text-emerald-700 dark:text-emerald-300">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <span>{uploadSuccess}</span>
        </div>
      )}

      {uploadError && (
        <div className="flex items-center gap-2 p-3 bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-900 rounded-xl text-xs text-rose-700 dark:text-rose-300">
          <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
          <span>{uploadError}</span>
        </div>
      )}

      {documents.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No documents uploaded"
          description="Upload your syllabus, lecture notes, or lab sheets (PDF, TXT, DOCX) to ask questions with Document AI!"
          actionText="Upload First Document"
          onAction={() => fileInputRef.current?.click()}
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Document List */}
          <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
              <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200">
                Uploaded Files ({documents.length})
              </h3>
              <span className="text-[10px] text-slate-400">PDF, TXT, DOCX</span>
            </div>

            <div className="space-y-2 max-h-[500px] overflow-y-auto">
              {documents.map((doc) => {
                const docId = doc.id;
                const isSelected = String(selectedDoc?.id || documents[0]?.id) === String(docId);
                const docName = doc.filename || doc.name || 'Document';
                const docType = (doc.file_type || doc.fileType || 'FILE').toUpperCase();
                const docSize = Math.round((doc.size_bytes || doc.fileSize || 0) / 1024);
                const docDate = doc.uploaded_at || doc.uploadDate;
                const formattedDate = docDate ? new Date(docDate).toLocaleDateString() : '';

                return (
                  <div
                    key={docId}
                    onClick={() => setSelectedDocId(docId)}
                    className={`p-3 rounded-xl border cursor-pointer transition flex items-start justify-between ${
                      isSelected
                        ? 'border-indigo-600 bg-indigo-50/50 dark:bg-indigo-950/40 ring-1 ring-indigo-500/20'
                        : 'border-slate-100 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-start gap-2.5">
                      <div className="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 mt-0.5">
                        <FileCheck className="w-4 h-4" />
                      </div>
                      <div>
                        <p className="text-xs font-semibold text-slate-800 dark:text-slate-200 line-clamp-1">
                          {docName}
                        </p>
                        <div className="flex flex-wrap items-center gap-1.5 text-[10px] text-slate-400 mt-0.5">
                          <span>{docType}</span>
                          <span>•</span>
                          <span>{docSize} KB</span>
                          {formattedDate && (
                            <>
                              <span>•</span>
                              <span>{formattedDate}</span>
                            </>
                          )}
                          <span className="ml-1 px-1.5 py-0.5 rounded text-[9px] font-semibold bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300">
                            Ready
                          </span>
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(docId, docName);
                      }}
                      className="text-slate-400 hover:text-rose-500 p-1 cursor-pointer transition"
                      title="Delete document"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Document AI / RAG Question Answering Area */}
          <div className="lg:col-span-2 p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-indigo-600" />
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                    Document AI Query: {selectedDoc?.filename || selectedDoc?.name || 'Selected Document'}
                  </h3>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 font-semibold">
                  RAG Active
                </span>
              </div>

              {/* RAG explanation banner */}
              <div className="mt-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 text-slate-600 dark:text-slate-300 text-xs">
                💡 <strong>Retrieval-Augmented Generation (RAG):</strong> Grounded question answering based on your uploaded document text.
              </div>

              {/* Sample Prompts */}
              <div className="mt-3">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                  Click a Sample RAG Prompt:
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {ragPrompts.map((p, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setQaQuery(p);
                        handleAskQuestion(p);
                      }}
                      className="text-[11px] px-2.5 py-1 rounded-lg bg-white dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 transition cursor-pointer"
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>

              {/* QA Answer View */}
              <div className="mt-4 p-4 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200/60 dark:border-slate-800 min-h-[200px] text-xs">
                {isAsking ? (
                  <LoadingSpinner text="Retrieving context and generating answer from document..." />
                ) : qaAnswer ? (
                  <div className="space-y-2">
                    <span className="text-[10px] font-bold text-indigo-600 uppercase tracking-wider block">
                      AI Document Response:
                    </span>
                    <div className="whitespace-pre-wrap leading-relaxed text-slate-800 dark:text-slate-200">
                      {qaAnswer}
                    </div>
                  </div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-center text-slate-400 py-10">
                    <BookOpen className="w-8 h-8 text-slate-300 dark:text-slate-700 mb-2" />
                    <span>Select a prompt above or type a specific question about this document below.</span>
                  </div>
                )}
              </div>
            </div>

            {/* Input Bar */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleAskQuestion();
              }}
              className="flex items-center gap-2 pt-2"
            >
              <input
                type="text"
                value={qaQuery}
                onChange={(e) => setQaQuery(e.target.value)}
                placeholder="Ask about this document: 'What is normalization?' or 'Summarize key takeaways'..."
                className="flex-1 px-4 py-2.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <button
                type="submit"
                disabled={!qaQuery.trim() || isAsking}
                className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-indigo-600/20 active:scale-95 disabled:opacity-50 cursor-pointer"
              >
                <span>Ask</span>
                <Send className="w-3.5 h-3.5" />
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
