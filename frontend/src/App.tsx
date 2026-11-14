import { useState, type FormEvent } from 'react'
import { Building2, FileUp, FileText, ExternalLink, AlertCircle, CheckCircle2 } from 'lucide-react'

type Evidence = { page: number; quote: string }
type Finding = { text: string; evidence: Evidence[] }
type Decision = {
  document_title: string
  summary: Finding
  proposed_changes: Finding[]
  affected_groups: Finding[]
  potential_benefits: Finding[]
  potential_tradeoffs: Finding[]
  participation: Finding[]
  unknowns: string[]
}

function Findings({ title, items }: { title: string; items: Finding[] }) {
  return <section className="result-section"><h3>{title}</h3>
    {items.length === 0 ? <p className="muted">Not confirmed in the supplied document.</p> :
      items.map((item, i) => <div className="finding" key={i}><p>{item.text}</p>
        {item.evidence.map((e, j) => <p className="evidence" key={j}><FileText size={14} /> PDF p. {e.page}: “{e.quote}”</p>)}
      </div>)}
  </section>
}

export default function App() {
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<Decision | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!file) return
    setBusy(true); setError(''); setResult(null)
    try {
      const body = new FormData()
      body.append('file', file)
      const response = await fetch('/api/analyze', { method: 'POST', body })
      const data = await response.json()
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Analysis failed. Try another PDF.')
      setResult(data as Decision)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error')
    } finally { setBusy(false) }
  }

  return <div className="site">
    <header><div className="brand"><Building2 size={25} /> <span>CivicLens</span></div><span className="top-tag">CIVIC Hack · Prototype</span></header>
    <main>
      <div className="hero"><p className="eyebrow">MUNICIPAL DECISIONS, MADE CLEAR</p>
        <h1>Understand what your city is deciding.</h1>
        <p className="lede">Upload an official municipal proposal to explore what may change, who might be affected, and opportunities to participate.</p>
      </div>
      <form className="upload-card" onSubmit={handleSubmit}>
        <div className="upload-heading"><FileUp size={23} /><div><h2>Analyze a municipal document</h2><p>Text-based PDF · max 10 MB · up to 25 pages</p></div></div>
        <label className="drop-area"><input type="file" accept="application/pdf,.pdf" onChange={e => { setFile(e.target.files?.[0] ?? null); setResult(null); setError('') }} />
          <FileText size={25} /><span>{file?.name ?? 'Choose a PDF to upload'}</span>
        </label>
        <button disabled={!file || busy}>{busy ? 'Analyzing document…' : 'Analyze proposal'}</button>
        <p className="privacy">Use public documents only. AI analysis requires a configured server-side API key.</p>
      </form>
      {error && <div className="error" role="alert"><AlertCircle size={18} />{error}</div>}
      {result && <div className="results" aria-live="polite">
        <div className="result-intro"><CheckCircle2 size={22}/><div><p className="eyebrow">DOCUMENT ANALYSIS</p><h2>{result.document_title}</h2></div></div>
        <div className="notice"><AlertCircle size={18}/><span>AI-generated draft. Verify each claim, deadline, and page reference against the official PDF. Potential impacts are not proven outcomes.</span></div>
        <section className="result-section"><h3>In plain language</h3><p>{result.summary.text}</p>
          {result.summary.evidence.map((e,i) => <p className="evidence" key={i}><FileText size={14}/> PDF p. {e.page}: “{e.quote}”</p>)}</section>
        <div className="result-grid">
          <Findings title="What might change?" items={result.proposed_changes}/>
          <Findings title="Who may be affected?" items={result.affected_groups}/>
          <Findings title="Potential benefits" items={result.potential_benefits}/>
          <Findings title="Potential harms and trade-offs" items={result.potential_tradeoffs}/>
        </div>
        <Findings title="Participation and next steps" items={result.participation}/>
        <section className="result-section"><h3>What remains unknown?</h3>
          {result.unknowns.length ? <ul>{result.unknowns.map((s,i)=><li key={i}>{s}</li>)}</ul> : <p className="muted">No additional uncertainties were identified; this does not guarantee completeness.</p>}</section>
        <p className="footnote"><ExternalLink size={14}/> Check the official municipal website for current notices before relying on this analysis.</p>
      </div>}
    </main>
    <footer>Made to support informed civic participation · Not an official municipal service</footer>
  </div>
}
