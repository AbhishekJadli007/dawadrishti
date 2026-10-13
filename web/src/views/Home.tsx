import { motion } from 'framer-motion'
import { ArrowRight, Building2, Clock, FileWarning, Fingerprint, MapPinned, Network, Search, ShieldCheck, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, axis, fmtInt, fmtPct, SEV_COLOR, tipStyle } from '../api'
import type { Go } from '../App'
import { IndiaMap } from '../components/IndiaMap'
import { AnimatedNumber, Badge, Button, Card, IconBubble, Reveal, Ring, SectionTitle, Spinner } from '../components/ui'

const EXAMPLES = ['Nestor Pharmaceuticals', 'Sresan Pharmaceuticals', 'Cipla']

export default function Home({ go, openMfr }: { go: Go; openMfr: (q: string) => void }) {
  const [s, setS] = useState<any>(null)
  const [o, setO] = useState<any>(null)
  const [er, setEr] = useState<any>(null)
  useEffect(() => {
    api.study().then(setS)
    api.overview().then(setO)
    api.quality().then((q) => setEr(q.entities.population)).catch(() => null)
  }, [])
  if (!s) return <Spinner label="Loading…" />
  const h = s.headline
  const search = (q: string) => go('check', { q })

  return (
    <div className="space-y-24 sm:space-y-32">
      {/* ------------------------------------------------ hero */}
      <section className="grid lg:grid-cols-[1.1fr_0.9fr] gap-10 lg:gap-6 items-center pt-2">
        <div>
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
            className="inline-flex items-center gap-2 rounded-full border border-teal-200 bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-700">
            <span className="h-2 w-2 rounded-full bg-ours pulse-dot text-ours" /> Real government data · {fmtInt(s.data.records_used)} failed batches since 2017
          </motion.div>
          <motion.h1 initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.12, duration: 0.6 }}
            className="mt-5 font-display text-[40px] sm:text-[56px] leading-[1.04] font-extrabold tracking-tight">
            Most failed medicines come from factories <span className="text-gradient-alert">we already knew about.</span>
          </motion.h1>
          <motion.p initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2, duration: 0.6 }}
            className="mt-5 text-lg text-muted max-w-xl leading-relaxed">
            India publishes every medicine batch that fails a government test. DawaDrishti turns those scattered alerts into one memory,
            so a hospital or state buyer can check a supplier <b className="text-ink">before</b> buying.
          </motion.p>
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.28, duration: 0.6 }} className="mt-7">
            <HeroSearch onSearch={search} />
            <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
              <span className="text-faint">Try</span>
              {EXAMPLES.map((e) => (
                <button key={e} onClick={() => search(e)} className="rounded-full border border-line bg-white px-3 py-1 text-muted hover:text-ink hover:border-teal-300 transition">{e}</button>
              ))}
            </div>
          </motion.div>
          <motion.button initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }} onClick={() => go('buyers')}
            className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-ours-2 hover:gap-3 transition-all">
            Or see what a buyer sees <ArrowRight size={16} />
          </motion.button>
        </div>
        <HeroVisual share={h.repeat_share} newLab={h.repeat_detected_by_new_lab} months={h.median_months_first_to_next} />
      </section>

      {/* ------------------------------------------------ how it works */}
      <section>
        <Reveal><SectionTitle center eyebrow="How it works" title="Three steps from a scattered record to a safer purchase" /></Reveal>
        <div className="relative grid md:grid-cols-3 gap-5">
          <svg className="hidden md:block absolute left-[16%] right-[16%] top-[52px] h-4 w-[68%] pointer-events-none" viewBox="0 0 100 4" preserveAspectRatio="none">
            <motion.path d="M0 2 H100" stroke="#5eead4" strokeWidth="2" strokeDasharray="6 6" fill="none" vectorEffect="non-scaling-stroke"
              initial={{ pathLength: 0 }} whileInView={{ pathLength: 1 }} viewport={{ once: true }} transition={{ duration: 1.4, ease: 'easeInOut' }} />
          </svg>
          {[
            { icon: FileWarning, tone: 'blood' as const, t: 'Government labs publish failures', d: `Every month CDSCO lists medicine batches that failed testing. ${fmtInt(s.data.records_used)} since 2017, spread across PDFs and a portal.` },
            { icon: Fingerprint, tone: 'indigo' as const, t: 'We join them into one memory', d: er ? `The same factory is written ${fmtInt(er.distinct_raw_strings)} different ways. We resolve them into ${fmtInt(er.units)} factories, and we test how well.` : 'The same factory is written thousands of ways. We resolve them into one record per factory, and we test how well.' },
            { icon: ShieldCheck, tone: 'ours' as const, t: 'Buyers check before they buy', d: 'One lookup at ordering and at delivery: the factory\'s record, and a clear answer on what to do now.' },
          ].map((x, i) => (
            <Reveal key={x.t} delay={i * 0.12}>
              <Card hover className="p-6 h-full relative bg-white">
                <div className="flex items-center gap-3">
                  <IconBubble icon={x.icon} tone={x.tone} size={52} />
                  <span className="font-display text-sm font-bold text-faint">STEP {i + 1}</span>
                </div>
                <div className="mt-4 font-display text-lg font-bold">{x.t}</div>
                <p className="mt-2 text-[15px] text-muted leading-relaxed">{x.d}</p>
              </Card>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ------------------------------------------------ what the record shows */}
      <section>
        <Reveal><SectionTitle eyebrow="What the record shows" title="Failures repeat, and they move" sub="Every number below comes from CDSCO's published alerts, September 2017 to August 2026." /></Reveal>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Stat icon={Clock} tone="amber" delay={0} value={<><AnimatedNumber value={h.median_months_first_to_next} format={(v) => v.toFixed(0)} /> months</>}
            label="Typical gap between a factory's first failure and its next one" />
          <Stat icon={Network} tone="indigo" delay={0.08} value={<AnimatedNumber value={100 * h.repeat_detected_by_new_lab} format={(v) => `${v.toFixed(0)}%`} />}
            label="of repeat failures were caught by a lab that had never caught that factory before" />
          <Stat icon={MapPinned} tone="ours" delay={0.16} value={<AnimatedNumber value={100 * h.repeat_detected_in_new_state} format={(v) => `${v.toFixed(0)}%`} />}
            label="were caught in a different state. The warning existed, just somewhere else." />
          <Stat icon={Building2} tone="blood" delay={0.24} value={<AnimatedNumber value={100 * h.top10pct_firms_share} format={(v) => `${v.toFixed(0)}%`} />}
            label="of all failures come from just 10% of factories" />
        </div>
        <Reveal delay={0.1}>
          <Card className="mt-5 p-6 sm:p-8 grid md:grid-cols-[1fr_1.2fr] gap-6 items-center overflow-hidden">
            <div>
              <Badge tone="waste"><Sparkles size={12} /> Why name-matching matters</Badge>
              <h3 className="mt-3 font-display text-xl font-bold">The same factory is spelled up to 14 different ways</h3>
              <p className="mt-2 text-muted text-[15px] leading-relaxed">Match names exactly and the repeat problem almost disappears. Match them carefully and it is two in three.
                That matching is the hardest part of this project, so we measure it openly.</p>
              <button onClick={() => go('proof', { sub: 'quality' })} className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-ours hover:gap-2.5 transition-all">How we check the matching <ArrowRight size={15} /></button>
            </div>
            <div className="space-y-4">
              <CompareBar label="Exact names" value={s.ablation['exact string'].repeat_share} color="#cbd5e1" />
              <CompareBar label="Names matched by DawaDrishti" value={h.repeat_share} color="#e11d48" highlight />
            </div>
          </Card>
        </Reveal>
      </section>

      {/* ------------------------------------------------ the honest part */}
      <section>
        <Reveal><SectionTitle eyebrow="The honest part" title="The disasters, checked against the record"
          sub="National alerts alone would not have warned anyone about these three. That is why the memory must also take results from state labs and buyers." /></Reveal>
        <div className="grid md:grid-cols-3 gap-5">
          {s.worked_cases.map((c: any, i: number) => (
            <Reveal key={c.case} delay={i * 0.1}>
              <Card hover className="p-6 h-full flex flex-col">
                <div className="font-display text-lg font-bold">{c.case.split(' (')[0]}</div>
                <div className="text-sm text-faint">{c.case.includes('(') ? c.case.split('(')[1].replace(')', '') : ''} · {c.note}</div>
                <div className="mt-5 flex items-end gap-6">
                  <div><div className="font-display text-5xl font-extrabold text-blood num">{c.alerts_before_incident}</div><div className="text-xs text-muted mt-1">alerts before the incident</div></div>
                  <div><div className="font-display text-3xl font-bold text-faint num">{c.national_alerts}</div><div className="text-xs text-muted mt-1">alerts in total</div></div>
                </div>
                <p className="mt-4 text-sm text-muted leading-relaxed flex-1">{caseReading(c)}</p>
                {c.national_alerts > 0 && <button onClick={() => openMfr(c.case.split(' (')[0])} className="mt-4 self-start inline-flex items-center gap-1.5 text-sm font-semibold text-ours hover:gap-2.5 transition-all">See the record <ArrowRight size={15} /></button>}
              </Card>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ------------------------------------------------ national picture */}
      {o && (
        <section>
          <Reveal><SectionTitle eyebrow="The national picture" title="Where failed batches are made, and when"
            sub="By the state in the manufacturer's address. States that test more find more, so read the map as where failures were found." /></Reveal>
          <div className="grid lg:grid-cols-[1fr_1.15fr] gap-5">
            <Reveal><IndiaMap geo={o.geography} height={430} /></Reveal>
            <Reveal delay={0.1}>
              <Card className="p-5 h-full">
                <div className="flex items-center justify-between">
                  <div className="font-display font-bold">Failed batches each month</div>
                  <div className="flex gap-3 text-xs text-muted">{['critical', 'major', 'minor'].map((k) => <span key={k} className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full" style={{ background: SEV_COLOR[k] }} />{k}</span>)}</div>
                </div>
                <div className="h-[350px] mt-3">
                  <ResponsiveContainer>
                    <AreaChart data={o.monthly} margin={{ top: 5, right: 6, left: -20, bottom: 0 }}>
                      <defs>{['critical', 'major', 'minor', 'unclassified'].map((k) => (
                        <linearGradient key={k} id={`g-${k}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={SEV_COLOR[k]} stopOpacity={0.55} /><stop offset="1" stopColor={SEV_COLOR[k]} stopOpacity={0.08} /></linearGradient>))}</defs>
                      <CartesianGrid vertical={false} stroke="#eef2f7" />
                      <XAxis dataKey="month" tick={axis} axisLine={false} tickLine={false} minTickGap={40} />
                      <YAxis tick={axis} axisLine={false} tickLine={false} />
                      <Tooltip contentStyle={tipStyle} />
                      {['critical', 'major', 'minor', 'unclassified'].map((k) => (
                        <Area key={k} type="monotone" dataKey={k} stackId="1" stroke={SEV_COLOR[k]} strokeWidth={1.5} fill={`url(#g-${k})`} animationDuration={1400} />
                      ))}
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </Reveal>
          </div>
        </section>
      )}

      {/* ------------------------------------------------ CTA */}
      <Reveal>
        <section className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-teal-600 via-teal-700 to-indigo-700 px-6 py-12 sm:px-12 sm:py-16 text-white">
          <div className="absolute inset-0 opacity-20 dot-grid" />
          <motion.div className="absolute -right-24 -top-24 h-72 w-72 rounded-full bg-white/10" animate={{ scale: [1, 1.12, 1] }} transition={{ repeat: Infinity, duration: 8 }} />
          <div className="relative grid md:grid-cols-[1.2fr_1fr] gap-8 items-center">
            <div>
              <h2 className="font-display text-3xl sm:text-4xl font-extrabold tracking-tight">Check any manufacturer in seconds.</h2>
              <p className="mt-3 text-teal-50/90 text-lg">Every published failure in one place, in plain language, with what the data does and doesn't tell you.</p>
            </div>
            <div className="space-y-3">
              <HeroSearch onSearch={search} dark />
              <button onClick={() => go('buyers')} className="inline-flex items-center gap-2 text-sm font-semibold text-white/90 hover:text-white">Or walk through the buyer demo <ArrowRight size={16} /></button>
            </div>
          </div>
        </section>
      </Reveal>
    </div>
  )
}

function HeroSearch({ onSearch, dark }: { onSearch: (q: string) => void; dark?: boolean }) {
  const [q, setQ] = useState('')
  return (
    <form onSubmit={(e) => { e.preventDefault(); if (q.trim().length > 1) onSearch(q.trim()) }}
      className={`flex items-center gap-2 rounded-full p-1.5 pl-5 shadow-[0_20px_40px_-20px_rgba(15,23,42,0.35)] ${dark ? 'bg-white' : 'bg-white border border-line'} focus-within:ring-4 focus-within:ring-teal-100 transition`}>
      <Search size={19} className="text-faint shrink-0" />
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Type a manufacturer's name…"
        className="flex-1 min-w-0 bg-transparent py-2.5 text-[16px] text-ink outline-none placeholder:text-faint" />
      <Button type="submit" className="!px-6 !py-3">Check</Button>
    </form>
  )
}

function HeroVisual({ share, newLab, months }: { share: number; newLab: number; months: number }) {
  return (
    <div className="relative mx-auto w-full max-w-[460px] aspect-square flex items-center justify-center">
      <motion.div className="absolute inset-6 rounded-full bg-gradient-to-br from-rose-100 via-white to-indigo-100" animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 40, ease: 'linear' }} />
      <div className="absolute inset-12 rounded-full bg-white shadow-[0_30px_60px_-30px_rgba(15,23,42,0.35)]" />
      <div className="relative">
        <Ring value={share} size={270} stroke={20} label="of failed batches came from a factory already on the record" />
      </div>
      <FloatChip className="left-0 top-[12%] float-slow" delay={0.6}>
        <span className="h-2.5 w-2.5 rounded-full bg-blood pulse-dot text-blood" /> New failure reported
      </FloatChip>
      <FloatChip className="right-0 top-[30%] float-mid" delay={0.8}>
        <ShieldCheck size={15} className="text-ours" /> Already on the record
      </FloatChip>
      <FloatChip className="left-[4%] bottom-[16%] float-mid" delay={1.0}>
        <Network size={15} className="text-ours-2" /> {fmtPct(newLab)} found by a new lab
      </FloatChip>
      <FloatChip className="right-[6%] bottom-[6%] float-slow" delay={1.2}>
        <Clock size={15} className="text-amber-600" /> next failure in ~{months.toFixed(0)} months
      </FloatChip>
    </div>
  )
}

function FloatChip({ children, className, delay }: { children: React.ReactNode; className: string; delay: number }) {
  return (
    <motion.div initial={{ opacity: 0, scale: 0.85 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay, type: 'spring', stiffness: 220, damping: 18 }}
      className={`absolute ${className}`}>
      <div className="flex items-center gap-2 rounded-full border border-line bg-white/95 px-3.5 py-2 text-[13px] font-semibold shadow-[0_14px_30px_-14px_rgba(15,23,42,0.35)] backdrop-blur">
        {children}
      </div>
    </motion.div>
  )
}

function Stat({ icon, tone, value, label, delay }: { icon: any; tone: 'amber' | 'indigo' | 'ours' | 'blood'; value: React.ReactNode; label: string; delay: number }) {
  return (
    <Reveal delay={delay}>
      <Card hover className="p-6 h-full">
        <IconBubble icon={icon} tone={tone} />
        <div className="mt-4 font-display text-4xl font-extrabold tracking-tight">{value}</div>
        <p className="mt-2 text-sm text-muted leading-relaxed">{label}</p>
      </Card>
    </Reveal>
  )
}

function CompareBar({ label, value, color, highlight }: { label: string; value: number; color: string; highlight?: boolean }) {
  return (
    <div>
      <div className="flex justify-between text-sm"><span className={highlight ? 'font-semibold' : 'text-muted'}>{label}</span>
        <span className={`font-display font-bold num ${highlight ? 'text-blood text-lg' : 'text-muted'}`}><AnimatedNumber value={100 * value} format={(v) => `${v.toFixed(1)}%`} /></span></div>
      <div className="mt-2 h-4 rounded-full bg-surface-3 overflow-hidden">
        <motion.div className="h-full rounded-full" style={{ background: color }} initial={{ width: 0 }} whileInView={{ width: `${100 * value}%` }}
          viewport={{ once: true }} transition={{ duration: 1.4, ease: [0.16, 1, 0.3, 1], delay: 0.2 }} />
      </div>
      <div className="text-xs text-faint mt-1">of failed batches look like repeats</div>
    </div>
  )
}

function caseReading(c: any): string {
  if (c.national_alerts === 0) return 'Never named in the national alerts. Its failures were found in state testing that never reached the national list.'
  if (c.alerts_before_incident === 0) return `No national alert before the incident. The first appeared in ${c.first_alert}, afterwards. Every alert since is on the record.`
  return `${c.alerts_before_incident} alerts were on record before the incident.`
}
