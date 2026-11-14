import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Building2, FileUp, FileText, ExternalLink, AlertCircle, ArrowRight, LoaderCircle, ShieldCheck } from 'lucide-react'

type Evidence = { page: number; quote: string }
type Finding = { text: string; evidence: Evidence[] }
type KeyFact = { kind: 'amount' | 'date'; label: string; value: string; evidence: Evidence[] }
type Decision = {
  document_title: string; summary: Finding; key_facts: KeyFact[]; proposed_changes: Finding[]; affected_groups: Finding[]
  potential_benefits: Finding[]; potential_tradeoffs: Finding[]; participation: Finding[]; unknowns: string[]
}
const categories = ['proposed_changes', 'affected_groups', 'potential_benefits', 'potential_tradeoffs', 'participation'] as const
// A long PDF is analyzed in up to 12 parts, one model call each; a local model takes about a minute per part.
// A single call still fails on the backend after OLLAMA_TIMEOUT_SECONDS (default 240).
const ANALYSIS_TIMEOUT_MS = 15 * 60_000
function isFinding(value: unknown): value is Finding {
  if (!value || typeof value !== 'object') return false
  const f = value as Finding
  return typeof f.text === 'string' && Array.isArray(f.evidence) && f.evidence.length > 0 && f.evidence.every(e => e && Number.isInteger(e.page) && e.page > 0 && typeof e.quote === 'string' && e.quote.trim().length > 0)
}
function isKeyFact(value: unknown): value is KeyFact {
  if (!value || typeof value !== 'object') return false
  const k = value as KeyFact
  return (k.kind === 'amount' || k.kind === 'date') && typeof k.value === 'string' && isFinding({ text: k.label, evidence: k.evidence })
}
function isDecision(value: unknown): value is Decision {
  if (!value || typeof value !== 'object') return false
  const d = value as Decision
  return typeof d.document_title === 'string' && isFinding(d.summary) && Array.isArray(d.key_facts) && d.key_facts.every(isKeyFact) && categories.every(k => Array.isArray(d[k]) && d[k].every(isFinding)) && Array.isArray(d.unknowns) && d.unknowns.every(s => typeof s === 'string')
}
function Findings({ title, items, source, potential = false, emptyMessage = "Not identified in the supplied text." }: { title: string; items: Finding[]; source: string; potential?: boolean; emptyMessage?: string }) {
  return <section className={`result-section ${potential ? 'potential' : ''}`}><h3>{title}</h3>
    {items.length === 0 ? <p className="muted">{emptyMessage}</p> : items.map((item, i) => <div className="finding" key={i}><p>{item.text}</p>
      <details><summary>View supporting excerpts · {item.evidence.length}</summary>
        {item.evidence.map((e, j) => <blockquote className="evidence" key={j}><p>“{e.quote}”</p><a href={`${source}#page=${e.page}`} target="_blank" rel="noreferrer">PDF page {e.page} <ExternalLink size={12}/></a></blockquote>)}
      </details></div>)}
  </section>
}
export default function App() {
  const [file, setFile] = useState<File | null>(null)
  const [source, setSource] = useState('')
  const [result, setResult] = useState<Decision | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const controller = useRef<AbortController | null>(null)
  const resultHeading = useRef<HTMLHeadingElement>(null)
  useEffect(() => { if (!file) { setSource(''); return }; const url = URL.createObjectURL(file); setSource(url); return () => URL.revokeObjectURL(url) }, [file])
  useEffect(() => { if (!busy) return; setElapsed(0); const id = window.setInterval(() => setElapsed(n => n + 1), 1000); return () => clearInterval(id) }, [busy])
  useEffect(() => { if (result) resultHeading.current?.focus() }, [result])
  useEffect(() => () => controller.current?.abort(), [])
  function selectFile(next: File | null) {
    setResult(null); setError(''); setFile(null)
    if (!next) return
    if (!next.name.toLowerCase().endsWith('.pdf')) { setError('Choose a PDF document.'); return }
    if (next.size === 0 || next.size > 10 * 1024 * 1024) { setError('Choose a non-empty PDF up to 10 MB.'); return }
    setFile(next)
  }
  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!file || busy) return
    setBusy(true); setError(''); setResult(null)
    const request = new AbortController(); controller.current = request
    let timedOut = false
    const timeout = window.setTimeout(() => { timedOut = true; request.abort() }, ANALYSIS_TIMEOUT_MS)
    try {
      const body = new FormData(); body.append('file', file)
      const response = await fetch('/api/analyze', { method: 'POST', body, signal: request.signal })
      const data: unknown = await response.json().catch(() => null)
      if (!response.ok) {
        const detail = data && typeof data === 'object' && 'detail' in data ? data.detail : null
        throw new Error(typeof detail === 'string' ? detail : 'The analysis service is unavailable. Check that the backend is running and try again.')
      }
      if (!isDecision(data)) throw new Error('The service returned an incomplete analysis. Please retry.')
      setResult(data)
    } catch (err) {
      setError(request.signal.aborted ? (timedOut ? 'Analysis timed out. Try a shorter PDF.' : 'Analysis cancelled. You can choose another PDF.') : err instanceof TypeError ? 'Could not connect to the analysis service. Check your connection and try again.' : err instanceof Error ? err.message : 'Analysis failed. Please retry.')
    } finally { clearTimeout(timeout); controller.current = null; setBusy(false) }
  }
  return <div className="site">
    <a className="skip-link" href="#upload">Skip to document upload</a>
    <header><a className="brand" href="#"><Building2 size={25}/><span>CivicScope<span className="brand-sub">COMMUNITY DECISION EXPLORER</span></span></a><a className="top-tag" href="#how-it-works">How it works <ArrowRight size={14}/></a></header>
    <main>
      <div className="hero"><p className="eyebrow"><span className="status-dot"/> A CLEARER VIEW OF LOCAL CHANGE</p><h1>See the decisions shaping <em>your community.</em></h1><p className="lede">From a lengthy proposal to a clearer picture. Explore what may change, who could be affected, and how to have your say.</p><div className="topic-tags"><span>Transportation</span><span>Housing & zoning</span><span>Public spaces & facilities</span></div></div>
      <div className="workspace"><form id="upload" className="upload-card" onSubmit={handleSubmit} aria-busy={busy}>
        <p className="eyebrow">01 / START WITH THE SOURCE</p><h2>Explore a municipal proposal</h2><p className="muted">Upload an official public document from any municipality.</p>
        <label className={`drop-area ${busy ? 'disabled' : ''}`}><input aria-label="Choose a municipal PDF" type="file" accept="application/pdf,.pdf" disabled={busy} onChange={e => selectFile(e.target.files?.[0] ?? null)}/><span className="file-icon"><FileUp size={27}/></span><strong>{file?.name ?? 'Choose a PDF document'}</strong><span>{file ? `${(file.size / (1024 * 1024)).toFixed(2)} MB · Ready to analyze` : 'Select a file from your device'}</span><small>Selectable text · Up to 10 MB · Maximum 300 pages</small></label>
        <button className="analyze-button" disabled={!file || busy}>{busy ? <><LoaderCircle className="spin" size={18}/> Analyzing document…</> : <>Explore this proposal <ArrowRight size={18}/></>}</button>
        {busy && <div className="progress"><p role="status">Reading the document and checking supporting excerpts. Long documents are read in parts and can take several minutes.</p><div><span aria-hidden="true">{elapsed}s elapsed</span><button type="button" className="text-button" onClick={() => controller.current?.abort()}>Cancel</button></div></div>}
        <p className="privacy"><ShieldCheck size={15}/> Public documents only. Extracted text is sent to an AI service for analysis.</p>
      </form><aside id="how-it-works" className="guide"><p className="eyebrow">FROM DOCUMENT TO UNDERSTANDING</p><h2>A source you can check.<br/>A decision you can explore.</h2><ol><li><strong>Bring the original</strong><p>A public proposal, planning notice, or staff report.</p></li><li><strong>Explore the details</strong><p>Changes, affected groups, possible benefits, and trade-offs.</p></li><li><strong>Check the evidence</strong><p>Follow page references back to your PDF before taking action.</p></li></ol><p className="guide-note">Built for different communities and proposal types. No account needed.</p></aside></div>
      {error && <div className="error" role="alert"><AlertCircle size={18}/><span>{error}</span></div>}
      {result && <div className="results"><div className="result-intro"><div><p className="eyebrow">02 / EXPLORE THE FINDINGS</p><h2 ref={resultHeading} tabIndex={-1}>{result.document_title}</h2><p className="muted">Source: {file?.name}</p></div><a className="source-link" href={source} target="_blank" rel="noreferrer"><FileText size={16}/> Open PDF</a></div>
        <div className="notice"><AlertCircle size={18}/><span>AI-generated interpretation. Excerpts were matched to the PDF text; this does not verify the meaning of each claim. Check the source and current municipal notices.</span></div>
        <Findings title="In plain language" items={[result.summary]} source={source}/>
        <Findings title="Key amounts and dates" items={result.key_facts.map(k => ({ text: `${k.value}: ${k.label}`, evidence: k.evidence }))} source={source} emptyMessage="No amounts or dates were identified in the supplied text."/>
        <div className="section-label">IN THE DOCUMENT <span>Source-based findings · verify the interpretation</span></div><div className="result-grid"><Findings title="What is proposed?" items={result.proposed_changes} source={source}/><Findings title="Who may be affected?" items={result.affected_groups} source={source}/></div>
        <div className="section-label">POTENTIAL IMPACTS <span>Possibilities, not established outcomes</span></div><div className="result-grid"><Findings title="Potential benefits" items={result.potential_benefits} source={source} potential/><Findings title="Potential trade-offs" items={result.potential_tradeoffs} source={source} potential/></div>
        <Findings title="Participation & next steps" items={result.participation} source={source} emptyMessage="No currently open participation opportunity is verified by this document. Check the municipality\u2019s official website."/><p className="footnote">Dates in the document may have passed. Confirm current opportunities on the municipality’s official website.</p>
        <section className="result-section"><h3>What remains uncertain?</h3>{result.unknowns.length ? <ul>{result.unknowns.map((s,i) => <li key={i}>{s}</li>)}</ul> : <p className="muted">No additional uncertainties were identified. This does not guarantee completeness.</p>}</section>
      </div>}
    </main><footer><span className="brand"><Building2 size={18}/> CivicScope</span><span>Supporting informed participation · Not an official municipal service</span><span>CIVIC Hack 2026 · Prototype</span></footer>
  </div>
}
