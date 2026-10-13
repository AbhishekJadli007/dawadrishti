import { animate, motion, useInView, useMotionValue, useTransform } from 'framer-motion'
import clsx from 'clsx'
import { useEffect, useRef, type ReactNode } from 'react'

export function Card({ children, className, hover, ...rest }: { children: ReactNode; className?: string; hover?: boolean } & React.HTMLAttributes<HTMLDivElement>) {
  return <div className={clsx('card', hover && 'card-hover', className)} {...rest}>{children}</div>
}

export function SectionTitle({ eyebrow, title, sub, right, center }: { eyebrow?: string; title: ReactNode; sub?: ReactNode; right?: ReactNode; center?: boolean }) {
  return (
    <div className={clsx('flex flex-wrap items-end gap-3 mb-6', center ? 'justify-center text-center' : 'justify-between')}>
      <div className={clsx(center && 'mx-auto')}>
        {eyebrow && <div className="text-xs uppercase tracking-[0.16em] text-ours font-semibold mb-2">{eyebrow}</div>}
        <h2 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-ink">{title}</h2>
        {sub && <p className={clsx('text-[15px] text-muted mt-2 max-w-2xl leading-relaxed', center && 'mx-auto')}>{sub}</p>}
      </div>
      {right}
    </div>
  )
}

/** Fades and lifts its children in when they scroll into view. */
export function Reveal({ children, delay = 0, className, y = 22 }: { children: ReactNode; delay?: number; className?: string; y?: number }) {
  return (
    <motion.div className={className} initial={{ opacity: 0, y }} whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }} transition={{ duration: 0.6, delay, ease: [0.16, 1, 0.3, 1] }}>
      {children}
    </motion.div>
  )
}

/** Number that counts up when it scrolls into view and re-animates on change. */
export function AnimatedNumber({ value, format = (v) => Math.round(v).toLocaleString('en-IN'), duration = 1.4, className }:
  { value: number; format?: (v: number) => string; duration?: number; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null)
  const inView = useInView(ref, { once: true, margin: '-40px' })
  const mv = useMotionValue(0)
  const text = useTransform(mv, (v) => format(v))
  useEffect(() => {
    if (!inView) return
    const c = animate(mv, value, { duration, ease: [0.16, 1, 0.3, 1] })
    return () => c.stop()
  }, [value, inView, duration, mv])
  return <motion.span ref={ref} className={clsx('num', className)}>{text}</motion.span>
}

/** Animated donut that fills to `value` (0..1) with the percentage counting up in the middle. */
export function Ring({ value, size = 240, stroke = 18, color = '#e11d48', track = '#f1f5f9', label, sub }:
  { value: number; size?: number; stroke?: number; color?: string; track?: string; label?: ReactNode; sub?: ReactNode }) {
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={track} strokeWidth={stroke} />
        <motion.circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={c} initial={{ strokeDashoffset: c }} whileInView={{ strokeDashoffset: c * (1 - value) }}
          viewport={{ once: true }} transition={{ duration: 1.8, ease: [0.16, 1, 0.3, 1], delay: 0.2 }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <div className="font-display font-extrabold tracking-tight" style={{ fontSize: size * 0.2 }}>
          <AnimatedNumber value={100 * value} format={(v) => `${v.toFixed(1)}%`} duration={1.8} />
        </div>
        {label && <div className="text-xs text-muted mt-1 px-6 leading-snug">{label}</div>}
        {sub}
      </div>
    </div>
  )
}

/** Pill-style switch with a sliding highlight. */
export function Segmented<T extends string>({ value, onChange, options, size = 'md', id }:
  { value: T; onChange: (v: T) => void; options: { value: T; label: ReactNode }[]; size?: 'sm' | 'md'; id: string }) {
  return (
    <div className="inline-flex rounded-full bg-surface-3/80 p-1 border border-line max-w-full overflow-x-auto">
      {options.map((o) => (
        <button key={o.value} onClick={() => onChange(o.value)}
          className={clsx('relative rounded-full whitespace-nowrap font-medium transition-colors', size === 'sm' ? 'px-3 py-1 text-xs' : 'px-4 py-1.5 text-sm',
            value === o.value ? 'text-ink' : 'text-muted hover:text-ink')}>
          {value === o.value && <motion.span layoutId={`seg-${id}`} className="absolute inset-0 rounded-full bg-white shadow-sm border border-line"
            transition={{ type: 'spring', stiffness: 420, damping: 34 }} />}
          <span className="relative flex items-center gap-1.5">{o.label}</span>
        </button>
      ))}
    </div>
  )
}

export function Badge({ children, tone = 'neutral', className }: { children: ReactNode; tone?: 'neutral' | 'good' | 'bad' | 'warn' | 'ours' | 'waste'; className?: string }) {
  const tones = {
    neutral: 'bg-surface-2 text-muted border-line',
    good: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    bad: 'bg-rose-50 text-rose-700 border-rose-200',
    warn: 'bg-amber-50 text-amber-800 border-amber-200',
    ours: 'bg-teal-50 text-teal-700 border-teal-200',
    waste: 'bg-violet-50 text-violet-700 border-violet-200',
  }
  return <span className={clsx('inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold', tones[tone], className)}>{children}</span>
}

export function Button({ children, onClick, variant = 'primary', disabled, className, type = 'button' }:
  { children: ReactNode; onClick?: () => void; variant?: 'primary' | 'ghost' | 'blood' | 'dark'; disabled?: boolean; className?: string; type?: 'button' | 'submit' }) {
  const v = {
    primary: 'bg-ours text-white hover:bg-teal-700 shadow-[0_8px_20px_-8px_rgba(13,148,136,0.6)]',
    blood: 'bg-blood text-white hover:bg-rose-700 shadow-[0_8px_20px_-8px_rgba(225,29,72,0.55)]',
    dark: 'bg-ink text-white hover:bg-slate-800',
    ghost: 'bg-white text-ink border border-line hover:bg-surface-2',
  }
  return (
    <motion.button whileTap={{ scale: 0.97 }} whileHover={{ y: -1 }} type={type} disabled={disabled} onClick={onClick}
      className={clsx('inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed', v[variant], className)}>
      {children}
    </motion.button>
  )
}

export function Field({ label, hint, children }: { label: string; hint?: ReactNode; children: ReactNode }) {
  return (
    <label className="block">
      <div className="flex items-baseline justify-between gap-2 mb-1.5">
        <span className="text-xs font-semibold text-muted">{label}</span>
        {hint && <span className="text-xs text-ink num">{hint}</span>}
      </div>
      {children}
    </label>
  )
}

export const inputCls = 'w-full rounded-xl bg-white border border-line px-3.5 py-2.5 text-sm text-ink outline-none transition focus:border-ours focus:ring-4 focus:ring-teal-100'

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-14 text-muted">
      <div className="relative h-11 w-11">
        <motion.div className="absolute inset-0 rounded-full border-[3px] border-teal-100 border-t-ours" animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 0.9, ease: 'linear' }} />
        <motion.div className="absolute inset-2 rounded-full border-[3px] border-indigo-100 border-b-ours-2" animate={{ rotate: -360 }} transition={{ repeat: Infinity, duration: 1.4, ease: 'linear' }} />
      </div>
      {label && <div className="text-sm">{label}</div>}
    </div>
  )
}

export function ErrorNote({ error }: { error: string }) {
  return <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
}

export function Delta({ base, value, better = 'lower', format = (x: number) => `${x > 0 ? '+' : ''}${x.toFixed(0)}%` }:
  { base: number; value: number; better?: 'lower' | 'higher'; format?: (x: number) => string }) {
  if (!base) return null
  const pct = (100 * (value - base)) / base
  const good = better === 'lower' ? pct < 0 : pct > 0
  if (Math.abs(pct) < 0.5) return <Badge>±0%</Badge>
  return <Badge tone={good ? 'good' : 'bad'}>{format(pct)}</Badge>
}

export function Source({ href, children }: { href: string; children: ReactNode }) {
  return <a href={href} target="_blank" rel="noreferrer" className="text-[12px] text-muted hover:text-ours underline decoration-dotted underline-offset-2">{children}</a>
}

/** An icon in a soft tinted circle. */
export function IconBubble({ icon: Icon, tone = 'ours', size = 44 }: { icon: any; tone?: 'ours' | 'blood' | 'indigo' | 'amber' | 'emerald'; size?: number }) {
  const tones = { ours: 'bg-teal-50 text-teal-600', blood: 'bg-rose-50 text-rose-600', indigo: 'bg-indigo-50 text-indigo-600', amber: 'bg-amber-50 text-amber-600', emerald: 'bg-emerald-50 text-emerald-600' }
  return <div className={clsx('rounded-2xl flex items-center justify-center shrink-0', tones[tone])} style={{ width: size, height: size }}><Icon size={size * 0.48} /></div>
}

export function coverColor(days: number): string {
  if (days < 1) return '#ef4444'
  if (days < 2) return '#f97316'
  if (days < 3) return '#f59e0b'
  return '#10b981'
}
