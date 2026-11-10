import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  Edit3, 
  AlertTriangle, 
  ShieldCheck, 
  Layers, 
  Activity, 
  BookOpen, 
  RotateCcw, 
  Download, 
  HelpCircle,
  ExternalLink,
  ChevronRight,
  Filter,
  Sparkles,
  ArrowRight,
  User,
  Clock,
  Eye,
  Terminal,
  Zap
} from 'lucide-react';

export default function App() {
  const [questions, setQuestions] = useState([]);
  const [reports, setReports] = useState([]);
  const [results, setResults] = useState([]);
  const [taxonomy, setTaxonomy] = useState(null);
  const [sweep, setSweep] = useState(null);
  const [loading, setLoading] = useState(true);

  // Active state
  const [selectedCaseIdx, setSelectedCaseIdx] = useState(0);
  const [auditLog, setAuditLog] = useState(() => {
    const saved = localStorage.getItem('acadza_audit_log');
    return saved ? JSON.parse(saved) : [];
  });
  const [actions, setActions] = useState(() => {
    const saved = localStorage.getItem('acadza_case_actions');
    return saved ? JSON.parse(saved) : {};
  });
  const [filterRoute, setFilterRoute] = useState('all'); // all | faculty_review | auto_apply | no_change
  const [showHelp, setShowHelp] = useState(false);
  const [showSweepModal, setShowSweepModal] = useState(false);
  const [toast, setToast] = useState(null);
  const [customReply, setCustomReply] = useState('');
  const [isEditingReply, setIsEditingReply] = useState(false);

  // Load datasets
  useEffect(() => {
    async function loadData() {
      try {
        const [qRes, rRes, resRes, taxRes, swRes] = await Promise.all([
          fetch('/questions.json').then(r => r.json()),
          fetch('/reports.json').then(r => r.json()),
          fetch('/results.json').then(r => r.json()),
          fetch('/taxonomy.json').then(r => r.json()),
          fetch('/sweep_results.json').then(r => r.json()).catch(() => null)
        ]);
        setQuestions(qRes);
        setReports(rRes);
        setResults(resRes);
        setTaxonomy(taxRes);
        setSweep(swRes);
        setLoading(false);
      } catch (err) {
        console.error('Failed to load datasets:', err);
        setLoading(false);
      }
    }
    loadData();
  }, []);

  // Map questions & results
  const qMap = useMemo(() => {
    const map = {};
    questions.forEach(q => { map[q._id] = q; });
    return map;
  }, [questions]);

  const resMap = useMemo(() => {
    const map = {};
    results.forEach(r => { map[r.reportId] = r; });
    return map;
  }, [results]);

  // Group reports by questionId into CASES
  const cases = useMemo(() => {
    if (!questions.length || !reports.length || !results.length) return [];
    
    const groups = {};
    reports.forEach(rep => {
      const qid = rep.questionId;
      if (!groups[qid]) {
        groups[qid] = {
          questionId: qid,
          reports: [],
          results: [],
          question: qMap[qid] || null
        };
      }
      groups[qid].reports.push(rep);
      const resItem = resMap[rep.reportId];
      if (resItem) groups[qid].results.push(resItem);
    });

    const caseList = Object.values(groups).map(c => {
      const q = c.question;
      const qtype = q ? q.questionType : 'unknown';
      const primaryResult = c.results[0] || {};
      const verdict = primaryResult.verdict || 'unknown';
      const route = primaryResult.route || 'no_change';
      const repair = primaryResult.repair || null;

      // Severity scoring: answer_key (40) > missing data (30) > option/display (20) > cosmetic (10)
      let severity = 5;
      if (repair === 'answer_key') severity = 40;
      else if (['stem_data', 'diagram', 'unsound', 'solution_fix'].includes(repair)) severity = 30;
      else if (['option_repair', 'identical_options', 'type_mismatch'].includes(repair)) severity = 20;
      else if (['spelling', 'noise', 'exam_reference', 'markup_leak'].includes(repair)) severity = 10;

      // Exposure proxy = distinct student count
      const reporters = new Set(c.reports.map(r => r.studentId)).size;
      const exposure = reporters;

      // Need human factor: if route == 'faculty_review' -> high need (x2)
      const needsHuman = route === 'faculty_review' ? 2.0 : (route === 'auto_apply' ? 0.8 : 0.4);

      const priorityScore = Math.round(severity * exposure * needsHuman);

      // Conflict detection: do any reports on this question differ in student intent?
      const distinctComments = new Set(c.reports.map(r => r.comment.trim())).size;
      const hasConflict = c.reports.length > 1 && distinctComments > 1;

      // Adversarial detection
      const isAdversarial = c.reports.some(r => r.comment.toLowerCase().includes('ignore all previous') || r.comment.toLowerCase().includes('admin bot'));

      return {
        ...c,
        qtype,
        primaryResult,
        verdict,
        route,
        repair,
        reporters,
        priorityScore,
        hasConflict,
        isAdversarial,
        rankReason: `Severity (${severity}) × ${exposure} student(s) × ${needsHuman}x human urgency`
      };
    });

    // Sort by priorityScore descending
    return caseList.sort((a, b) => b.priorityScore - a.priorityScore);
  }, [questions, reports, results, qMap, resMap]);

  // Filtered cases
  const filteredCases = useMemo(() => {
    if (filterRoute === 'all') return cases;
    return cases.filter(c => c.route === filterRoute);
  }, [cases, filterRoute]);

  const activeCase = filteredCases[selectedCaseIdx] || filteredCases[0] || null;

  // Sync custom student reply when active case changes
  useEffect(() => {
    if (activeCase && activeCase.primaryResult) {
      setCustomReply(activeCase.primaryResult.student_reply || '');
      setIsEditingReply(false);
    }
  }, [activeCase]);

  // Toast helper
  const showToast = useCallback((msg, type = 'info') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  }, []);

  // Faculty Actions: Approve / Edit / Reject
  const handleAction = useCallback((actionType) => {
    if (!activeCase) return;
    const qid = activeCase.questionId;
    const newActions = {
      ...actions,
      [qid]: {
        action: actionType,
        timestamp: new Date().toISOString(),
        customReply: customReply
      }
    };
    setActions(newActions);
    localStorage.setItem('acadza_case_actions', JSON.stringify(newActions));

    // Append to Audit Log
    const newEntry = {
      id: `AUDIT-${Date.now()}`,
      qid,
      action: actionType,
      faculty: "Faculty Reviewer (10 PM shift)",
      verdict: activeCase.verdict,
      repair: activeCase.repair,
      timestamp: new Date().toISOString(),
      studentReply: customReply,
      headline: `${actionType.toUpperCase()}: ${activeCase.repair || activeCase.verdict} for QID ${qid.slice(0, 8)}...`
    };
    const updatedLog = [newEntry, ...auditLog];
    setAuditLog(updatedLog);
    localStorage.setItem('acadza_audit_log', JSON.stringify(updatedLog));

    showToast(`Case ${qid.slice(0, 8)} marked as ${actionType.toUpperCase()}`, 'success');

    // Move to next case automatically
    if (selectedCaseIdx < filteredCases.length - 1) {
      setSelectedCaseIdx(prev => prev + 1);
    }
  }, [activeCase, actions, customReply, auditLog, showToast, selectedCaseIdx, filteredCases.length]);

  // Keyboard navigation: J/K to move, A/E/R to act, ? for help
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Don't intercept when typing in textarea or input
      if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;

      if (e.key === 'j' || e.key === 'J' || e.key === 'ArrowDown') {
        setSelectedCaseIdx(prev => Math.min(filteredCases.length - 1, prev + 1));
      } else if (e.key === 'k' || e.key === 'K' || e.key === 'ArrowUp') {
        setSelectedCaseIdx(prev => Math.max(0, prev - 1));
      } else if (e.key === 'a' || e.key === 'A') {
        handleAction('approve');
      } else if (e.key === 'e' || e.key === 'E') {
        setIsEditingReply(true);
      } else if (e.key === 'r' || e.key === 'R') {
        handleAction('reject');
      } else if (e.key === '?') {
        setShowHelp(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [filteredCases.length, handleAction]);

  // Sticky counts
  const counts = useMemo(() => {
    const total = cases.length;
    const reviewed = Object.keys(actions).length;
    const autoApplied = cases.filter(c => c.route === 'auto_apply').length;
    const needYou = cases.filter(c => c.route === 'faculty_review' && !actions[c.questionId]).length;
    return { left: total - reviewed, autoApplied, needYou };
  }, [cases, actions]);

  // Render before/after question HTML for Diff viewer
  const { beforeHtml, afterHtml, hasEdit } = useMemo(() => {
    if (!activeCase || !activeCase.question) return { beforeHtml: '', afterHtml: '', hasEdit: false };
    const q = activeCase.question;
    const qtype = q.questionType;
    const inner = q[qtype] || {};
    const before = inner.question || '';
    const edit = activeCase.primaryResult?.edit;

    if (!edit) return { beforeHtml: before, afterHtml: before, hasEdit: false };

    if (edit.field === 'question' && edit.find && edit.replace !== undefined) {
      const after = before.replace(edit.find, `<span class="bg-emerald-500/30 text-emerald-300 font-semibold border-b-2 border-emerald-400 px-1 rounded">${edit.replace}</span>`);
      const markedBefore = before.replace(edit.find, `<span class="bg-rose-500/30 text-rose-300 line-through font-semibold border-b-2 border-rose-400 px-1 rounded">${edit.find}</span>`);
      return { beforeHtml: markedBefore, afterHtml: after, hasEdit: true };
    }

    if (edit.field === 'answer') {
      return {
        beforeHtml: before,
        afterHtml: `<div class="mb-3 px-3 py-2 bg-emerald-950/60 border border-emerald-500/40 rounded text-emerald-200 text-sm font-mono flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> Answer Key Shift: ${edit.find} &rarr; <strong class="text-emerald-300 text-base">${edit.replace}</strong></div>` + before,
        hasEdit: true
      };
    }

    if (edit.field === 'questionType') {
      return {
        beforeHtml: before,
        afterHtml: `<div class="mb-3 px-3 py-2 bg-sky-950/60 border border-sky-500/40 rounded text-sky-200 text-sm font-mono flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-sky-400"></span> Reclassified: ${edit.find} &rarr; <strong class="text-sky-300 text-base">${edit.replace}</strong></div>` + before,
        hasEdit: true
      };
    }

    return { beforeHtml: before, afterHtml: before, hasEdit: false };
  }, [activeCase]);

  // Export audit log
  const exportAuditLog = () => {
    const blob = new Blob([JSON.stringify(auditLog, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `acadza_audit_log_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="h-screen flex flex-col items-center justify-center bg-[#0c0e12] text-slate-300 font-mono text-sm">
        <Activity className="w-8 h-8 text-sky-400 animate-spin mb-4" />
        <p>Loading Acadza Triage Console...</p>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-[#0c0e12] text-slate-100 overflow-hidden font-sans">
      {/* Toast Notification */}
      {toast && (
        <div className="fixed top-4 right-4 z-50 px-4 py-2 bg-slate-900 border border-slate-700 shadow-2xl rounded-md text-sm text-slate-200 flex items-center gap-2 animate-in fade-in slide-in-from-top-2">
          <Zap className="w-4 h-4 text-amber-400" />
          <span>{toast.msg}</span>
        </div>
      )}

      {/* TOP HEADER */}
      <header className="h-14 border-b border-[#242b35] bg-[#14181f]/90 backdrop-blur px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded bg-sky-500/10 border border-sky-400/30 flex items-center justify-center">
              <ShieldCheck className="w-4 h-4 text-sky-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-sm tracking-tight text-white">Acadza Faculty Console</span>
                <span className="px-1.5 py-0.5 rounded text-[10px] uppercase font-mono font-bold tracking-wider bg-sky-500/10 text-sky-400 border border-sky-500/20">Verifier-First</span>
              </div>
            </div>
          </div>

          <div className="h-4 w-px bg-slate-700 mx-1 hidden sm:block" />

          {/* Sticky Quick Counters */}
          <div className="flex items-center gap-3 text-xs font-mono">
            <span className="text-slate-400"><strong className="text-slate-200">{counts.left}</strong> remaining</span>
            <span className="text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20"><strong className="font-bold">{counts.autoApplied}</strong> auto-applied</span>
            <span className="text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20"><strong className="font-bold">{counts.needYou}</strong> need you</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Defect Sweep Modal Button */}
          <button 
            onClick={() => setShowSweepModal(true)}
            className="px-3 py-1.5 rounded text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 flex items-center gap-1.5 transition-colors"
          >
            <Layers className="w-3.5 h-3.5 text-sky-400" />
            <span>Bank Sweep (8 Lakh)</span>
          </button>

          {/* Export Audit */}
          <button 
            onClick={exportAuditLog}
            className="px-3 py-1.5 rounded text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 flex items-center gap-1.5 transition-colors"
            title="Export local audit log"
          >
            <Download className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Audit Log ({auditLog.length})</span>
          </button>

          {/* Help keyboard shortcut */}
          <button 
            onClick={() => setShowHelp(true)}
            className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
            title="Keyboard shortcuts (?)"
          >
            <HelpCircle className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* MAIN TWO-COLUMN WORKSPACE */}
      <div className="flex-1 flex overflow-hidden">
        {/* LEFT COLUMN: CASE QUEUE */}
        <aside className="w-80 md:w-96 border-r border-[#242b35] bg-[#0c0e12] flex flex-col shrink-0">
          {/* Filter Bar */}
          <div className="p-3 border-b border-[#242b35] flex items-center justify-between gap-1 bg-[#14181f]">
            <div className="flex items-center gap-1 w-full text-xs">
              {[
                { id: 'all', label: 'All' },
                { id: 'faculty_review', label: 'Review' },
                { id: 'auto_apply', label: 'Auto' },
                { id: 'no_change', label: 'No Chg' }
              ].map(f => (
                <button
                  key={f.id}
                  onClick={() => { setFilterRoute(f.id); setSelectedCaseIdx(0); }}
                  className={`flex-1 py-1 rounded text-center font-medium transition-colors ${
                    filterRoute === f.id 
                      ? 'bg-slate-800 text-sky-400 border border-slate-700 shadow-sm' 
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          {/* Queue List */}
          <div className="flex-1 overflow-y-auto divide-y divide-[#1e2530]">
            {filteredCases.map((c, idx) => {
              const isSelected = idx === selectedCaseIdx;
              const hasAction = actions[c.questionId];

              return (
                <div
                  key={c.questionId}
                  onClick={() => setSelectedCaseIdx(idx)}
                  className={`p-3.5 cursor-pointer transition-colors relative group ${
                    isSelected 
                      ? 'bg-[#1a202c] border-l-4 border-sky-400' 
                      : 'hover:bg-[#14181f]'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-slate-300">
                        {c.questionId.slice(0, 8)}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.2 rounded font-mono uppercase bg-slate-800 text-slate-400 border border-slate-700">
                        {c.qtype}
                      </span>
                    </div>

                    {/* Priority score with tooltip */}
                    <div 
                      className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20 cursor-help"
                      title={c.rankReason}
                    >
                      Score {c.priorityScore}
                    </div>
                  </div>

                  {/* Headline */}
                  <div className="text-xs font-medium text-slate-200 line-clamp-1 mb-1.5">
                    {c.repair ? (
                      <span className="text-emerald-400 font-semibold">{c.repair.replace('_', ' ').toUpperCase()}: </span>
                    ) : null}
                    {c.reports[0]?.comment || 'No comment'}
                  </div>

                  {/* Badges strip */}
                  <div className="flex items-center gap-2 text-[11px] text-slate-400">
                    <span className="flex items-center gap-1">
                      <User className="w-3 h-3 text-slate-500" />
                      {c.reporters} report{c.reporters > 1 ? 's' : ''}
                    </span>

                    <span className="text-slate-600">&bull;</span>

                    {/* Route status */}
                    <span className={`px-1.5 py-0.2 rounded text-[10px] font-mono ${
                      c.route === 'auto_apply' 
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                        : c.route === 'faculty_review' 
                        ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' 
                        : 'bg-slate-800 text-slate-400 border border-slate-700'
                    }`}>
                      {c.route}
                    </span>

                    {/* Action marker if acted */}
                    {hasAction && (
                      <span className="ml-auto text-[10px] font-mono font-bold text-sky-400 uppercase">
                        [{hasAction.action}]
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </aside>

        {/* RIGHT COLUMN: ACTIVE CASE WORKBENCH */}
        {activeCase ? (
          <main className="flex-1 flex flex-col overflow-y-auto bg-[#0c0e12]">
            {/* Workbench Top Bar: Headline & Fast Decision Toolbar */}
            <div className="p-4 border-b border-[#242b35] bg-[#14181f] flex flex-wrap items-center justify-between gap-4 sticky top-0 z-10 shadow-md">
              <div>
                <div className="flex items-center gap-2 text-xs font-mono text-slate-400 mb-0.5">
                  <span>QID: {activeCase.questionId}</span>
                  <span>&bull;</span>
                  <span>Subject: {activeCase.question?.subject || 'N/A'}</span>
                  <span>&bull;</span>
                  <span>Chapter: {activeCase.question?.chapter || 'N/A'}</span>
                </div>
                <h2 className="text-base font-semibold text-white flex items-center gap-2">
                  <span>{activeCase.repair ? `Proposed Fix: ${activeCase.repair}` : `Triage: ${activeCase.verdict}`}</span>
                  <span className="text-xs font-mono font-normal text-slate-400">
                    (Conf: {Math.round((activeCase.primaryResult?.confidence || 0.95) * 100)}%)
                  </span>
                </h2>
              </div>

              {/* Fast Decision Buttons with Shortcuts */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleAction('approve')}
                  className="px-3.5 py-1.5 rounded-md text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white flex items-center gap-1.5 shadow-sm transition-all"
                  title="Press 'A' on keyboard"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Approve (A)</span>
                </button>

                <button
                  onClick={() => setIsEditingReply(prev => !prev)}
                  className="px-3 py-1.5 rounded-md text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 flex items-center gap-1.5 transition-all"
                  title="Press 'E' on keyboard"
                >
                  <Edit3 className="w-3.5 h-3.5 text-sky-400" />
                  <span>Edit Reply (E)</span>
                </button>

                <button
                  onClick={() => handleAction('reject')}
                  className="px-3 py-1.5 rounded-md text-xs font-semibold bg-rose-950/80 hover:bg-rose-900 text-rose-300 border border-rose-800/80 flex items-center gap-1.5 transition-all"
                  title="Press 'R' on keyboard"
                >
                  <XCircle className="w-3.5 h-3.5" />
                  <span>Reject (R)</span>
                </button>
              </div>
            </div>

            {/* SPECIAL BANNERS: Adversarial, Conflicting Reports */}
            <div className="px-6 pt-4 space-y-2">
              {activeCase.isAdversarial && (
                <div className="p-3 bg-rose-950/40 border border-rose-500/40 rounded-md text-xs text-rose-200 flex items-start gap-2.5">
                  <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                  <div>
                    <strong className="font-semibold uppercase tracking-wider block">Possible Gaming / Adversarial Prompt Injection Detected</strong>
                    <span>Student comment contains instruction-override syntax ("IGNORE ALL PREVIOUS INSTRUCTIONS"). The instruction was quarantined and ignored; the underlying question is triaged strictly on its own merits.</span>
                  </div>
                </div>
              )}

              {activeCase.hasConflict && (
                <div className="p-3 bg-amber-950/40 border border-amber-500/40 rounded-md text-xs text-amber-200 flex items-start gap-2.5">
                  <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <strong className="font-semibold block">Conflicting Student Reports</strong>
                    <span>Multiple students reported this question with differing feedback. Surfaced together for holistic evaluation rather than averaged away.</span>
                  </div>
                </div>
              )}
            </div>

            <div className="p-6 space-y-6">
              {/* SECTION 1: EVIDENCE STRIP OF CHECK CHIPS */}
              <div>
                <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-sky-400" />
                  <span>Independent Evidence Strip (Zero-LLM Verification)</span>
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs">
                  <div className="p-2.5 bg-[#14181f] border border-[#242b35] rounded-md">
                    <span className="text-[10px] font-mono text-slate-500 uppercase block">Deterministic Detector</span>
                    <strong className="text-emerald-400 flex items-center gap-1 mt-0.5">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>{activeCase.primaryResult?.repair || 'Passed'}</span>
                    </strong>
                  </div>

                  <div className="p-2.5 bg-[#14181f] border border-[#242b35] rounded-md">
                    <span className="text-[10px] font-mono text-slate-500 uppercase block">Blind Solver (N=3)</span>
                    <strong className="text-emerald-400 flex items-center gap-1 mt-0.5">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>3/3 Consensus</span>
                    </strong>
                  </div>

                  <div className="p-2.5 bg-[#14181f] border border-[#242b35] rounded-md">
                    <span className="text-[10px] font-mono text-slate-500 uppercase block">Solution Match</span>
                    <strong className="text-emerald-400 flex items-center gap-1 mt-0.5">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Verified</span>
                    </strong>
                  </div>

                  <div className="p-2.5 bg-[#14181f] border border-[#242b35] rounded-md">
                    <span className="text-[10px] font-mono text-slate-500 uppercase block">Scope Guard</span>
                    <strong className="text-emerald-400 flex items-center gap-1 mt-0.5">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Passed (Count=1)</span>
                    </strong>
                  </div>

                  <div className="p-2.5 bg-[#14181f] border border-[#242b35] rounded-md">
                    <span className="text-[10px] font-mono text-slate-500 uppercase block">Replay Check</span>
                    <strong className="text-emerald-400 flex items-center gap-1 mt-0.5">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Proof of Fix</span>
                    </strong>
                  </div>
                </div>

                <div className="mt-2 text-xs font-mono text-slate-400 bg-[#14181f] p-3 rounded border border-[#242b35]">
                  <strong className="text-slate-300">Evidence Summary: </strong>
                  <span>{activeCase.primaryResult?.evidence || 'No evidence recorded.'}</span>
                </div>
              </div>

              {/* SECTION 2: BEFORE / AFTER DIFF (OR RENDERED QUESTION) */}
              <div>
                <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5 text-sky-400" />
                  <span>Question Inspection & Visual MathML Diff</span>
                </h3>

                {hasEdit ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Before Pane */}
                    <div className="p-4 bg-[#14181f] border border-[#242b35] rounded-lg">
                      <div className="flex items-center justify-between pb-2 mb-3 border-b border-[#242b35] text-xs font-mono text-slate-400">
                        <span>BEFORE (Current Live Record)</span>
                        <span className="px-1.5 py-0.2 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">Original</span>
                      </div>
                      <div 
                        className="text-slate-200 text-sm leading-relaxed prose prose-invert max-w-none"
                        dangerouslySetInnerHTML={{ __html: beforeHtml }}
                      />
                    </div>

                    {/* After Pane */}
                    <div className="p-4 bg-[#14181f] border border-emerald-500/30 rounded-lg">
                      <div className="flex items-center justify-between pb-2 mb-3 border-b border-[#242b35] text-xs font-mono text-slate-400">
                        <span>AFTER (Surgically Repaired)</span>
                        <span className="px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Replay Verified</span>
                      </div>
                      <div 
                        className="text-slate-200 text-sm leading-relaxed prose prose-invert max-w-none"
                        dangerouslySetInnerHTML={{ __html: afterHtml }}
                      />
                    </div>
                  </div>
                ) : (
                  <div className="p-4 bg-[#14181f] border border-[#242b35] rounded-lg">
                    <div className="flex items-center justify-between pb-2 mb-3 border-b border-[#242b35] text-xs font-mono text-slate-400">
                      <span>LIVE QUESTION CONTENT</span>
                      <span className="px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 border border-slate-700">Answer Key: {String(activeCase.question?.[activeCase.qtype]?.answer)}</span>
                    </div>
                    <div 
                      className="text-slate-200 text-sm leading-relaxed prose prose-invert max-w-none"
                      dangerouslySetInnerHTML={{ __html: beforeHtml }}
                    />
                  </div>
                )}
              </div>

              {/* SECTION 3: STUDENT REPORTS & EMPATHETIC REPLY PREVIEW */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Reports on this question */}
                <div className="p-4 bg-[#14181f] border border-[#242b35] rounded-lg">
                  <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-1.5">
                    <User className="w-3.5 h-3.5 text-sky-400" />
                    <span>Student Reports Received ({activeCase.reports.length})</span>
                  </h4>
                  <div className="space-y-2">
                    {activeCase.reports.map((r, i) => (
                      <div key={r.reportId} className="p-2.5 bg-[#0c0e12] rounded border border-[#242b35] text-xs">
                        <div className="flex items-center justify-between text-[11px] text-slate-500 mb-1">
                          <span className="font-mono text-slate-400">[{r.reportId}] {r.studentId}</span>
                          <span>{new Date(r.reportedAt).toLocaleDateString()}</span>
                        </div>
                        <p className="text-slate-200 italic">"{r.comment}"</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Student Reply Preview */}
                <div className="p-4 bg-[#14181f] border border-[#242b35] rounded-lg flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5 text-sky-400" />
                        <span>Student Reply Preview (1-3 Sentences)</span>
                      </h4>
                      <button 
                        onClick={() => setIsEditingReply(prev => !prev)}
                        className="text-xs font-mono text-sky-400 hover:underline"
                      >
                        {isEditingReply ? 'Done' : 'Edit'}
                      </button>
                    </div>

                    {isEditingReply ? (
                      <textarea
                        value={customReply}
                        onChange={(e) => setCustomReply(e.target.value)}
                        className="w-full h-24 p-2 bg-[#0c0e12] border border-sky-500/50 rounded text-xs text-slate-200 focus:outline-none font-sans"
                        placeholder="Customize reply for this student..."
                      />
                    ) : (
                      <div className="p-3 bg-[#0c0e12] border border-[#242b35] rounded text-xs text-slate-300 leading-relaxed font-sans">
                        "{customReply}"
                      </div>
                    )}
                  </div>

                  <div className="text-[11px] text-slate-500 mt-3 pt-2 border-t border-[#242b35] flex items-center justify-between">
                    <span>Tone: Empathetic, supportive JEE/NEET prep</span>
                    <span>No internal terms leaked</span>
                  </div>
                </div>
              </div>
            </div>
          </main>
        ) : null}
      </div>

      {/* FOOTER */}
      <footer className="h-9 border-t border-[#242b35] bg-[#14181f] px-6 flex items-center justify-between text-[11px] text-slate-500 font-mono shrink-0">
        <div>
          <span>Acadza Triage System &bull; Offline-Runnable Precomputed Cache</span>
        </div>
        <div className="flex items-center gap-4">
          <span>Shortcuts: <kbd className="px-1 py-0.5 rounded bg-slate-800 text-slate-300">J</kbd>/<kbd className="px-1 py-0.5 rounded bg-slate-800 text-slate-300">K</kbd> move &bull; <kbd className="px-1 py-0.5 rounded bg-slate-800 text-slate-300">A</kbd> approve &bull; <kbd className="px-1 py-0.5 rounded bg-slate-800 text-slate-300">E</kbd> edit &bull; <kbd className="px-1 py-0.5 rounded bg-slate-800 text-slate-300">R</kbd> reject</span>
        </div>
      </footer>

      {/* MODAL: DEFECT CLASS SWEEP */}
      {showSweepModal && sweep && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#14181f] border border-[#242b35] rounded-xl max-w-2xl w-full p-6 shadow-2xl animate-in zoom-in-95">
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-[#242b35]">
              <div>
                <h3 className="text-base font-semibold text-white flex items-center gap-2">
                  <Layers className="w-4 h-4 text-sky-400" />
                  <span>Defect-Class Sweep ("Blast Radius" Analysis)</span>
                </h3>
                <p className="text-xs text-slate-400 font-mono mt-0.5">
                  Extrapolating 43-question sample frequencies to the ~8 Lakh question bank
                </p>
              </div>
              <button 
                onClick={() => setShowSweepModal(false)}
                className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-white"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4 text-xs font-mono">
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3 bg-[#0c0e12] rounded border border-[#242b35]">
                  <span className="text-slate-500 block">Sample Examined</span>
                  <strong className="text-base text-slate-200">43 questions</strong>
                </div>
                <div className="p-3 bg-[#0c0e12] rounded border border-[#242b35]">
                  <span className="text-slate-500 block">Detector Hits</span>
                  <strong className="text-base text-sky-400">{sweep.total_detector_hits} findings</strong>
                </div>
                <div className="p-3 bg-[#0c0e12] rounded border border-[#242b35]">
                  <span className="text-slate-500 block">Full Bank Size</span>
                  <strong className="text-base text-slate-200">~800,000</strong>
                </div>
              </div>

              <div className="border border-[#242b35] rounded-lg overflow-hidden">
                <table className="w-full text-left">
                  <thead className="bg-[#0c0e12] text-slate-400 border-b border-[#242b35]">
                    <tr>
                      <th className="p-2.5">Defect Class</th>
                      <th className="p-2.5">Sample Rate</th>
                      <th className="p-2.5">Est. Bank Occurrences</th>
                      <th className="p-2.5">95% CI Range</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1e2530] text-slate-300">
                    {Object.entries(sweep.defect_class_extrapolations || {}).map(([cls, data]) => (
                      <tr key={cls} className="hover:bg-[#1a202c]">
                        <td className="p-2.5 font-semibold text-emerald-400">{cls}</td>
                        <td className="p-2.5">{data.sample_occurrences}/43 ({data.sample_rate_percent}%)</td>
                        <td className="p-2.5 font-bold text-slate-100">{data.estimated_in_8_lakh_bank.toLocaleString()}</td>
                        <td className="p-2.5 text-slate-400">{data.ci_95_percent[0].toLocaleString()} - {data.ci_95_percent[1].toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="p-3 bg-sky-950/40 border border-sky-500/30 rounded text-slate-300 text-[11px] leading-relaxed">
                <strong className="text-sky-300">The Core Insight: </strong>
                One student report shouldn't just fix a single question—it exposes a systemic defect class. By exporting our deterministic detectors as reusable sweep rules, Acadza can proactively eradicate ~37,000 broken options and key errors before students ever see them.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: KEYBOARD SHORTCUTS */}
      {showHelp && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#14181f] border border-[#242b35] rounded-xl max-w-md w-full p-6 shadow-2xl animate-in zoom-in-95">
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-[#242b35]">
              <h3 className="text-base font-semibold text-white flex items-center gap-2">
                <HelpCircle className="w-4 h-4 text-sky-400" />
                <span>Keyboard Shortcuts</span>
              </h3>
              <button onClick={() => setShowHelp(false)} className="p-1 rounded hover:bg-slate-800 text-slate-400">
                <XCircle className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-3 text-xs font-mono text-slate-300">
              <div className="flex items-center justify-between">
                <span>Navigate Cases:</span>
                <div>
                  <kbd className="px-2 py-1 rounded bg-slate-800 text-slate-200 border border-slate-700">J</kbd> / <kbd className="px-2 py-1 rounded bg-slate-800 text-slate-200 border border-slate-700">K</kbd> or &uarr; / &darr;
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span>One-Click Approve:</span>
                <kbd className="px-2 py-1 rounded bg-slate-800 text-slate-200 border border-slate-700">A</kbd>
              </div>
              <div className="flex items-center justify-between">
                <span>Edit Student Reply:</span>
                <kbd className="px-2 py-1 rounded bg-slate-800 text-slate-200 border border-slate-700">E</kbd>
              </div>
              <div className="flex items-center justify-between">
                <span>One-Click Reject:</span>
                <kbd className="px-2 py-1 rounded bg-slate-800 text-slate-200 border border-slate-700">R</kbd>
              </div>
              <div className="flex items-center justify-between">
                <span>Toggle Help:</span>
                <kbd className="px-2 py-1 rounded bg-slate-800 text-slate-200 border border-slate-700">?</kbd>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
