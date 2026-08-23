// Shared visual primitives ported from the newer SwarmShield UI/UX reference.
// Pure presentation only — no data/behavior. Kept dependency-light (no cva/clsx)
// to avoid touching the working build toolchain.

export function cx(...parts) {
  return parts.filter(Boolean).join(" ");
}

/** Glass panel — the base card surface used across the modernized screens. */
export function Panel({ className = "", children, glow = false, ...rest }) {
  return (
    <div
      className={cx(
        "rounded-2xl border border-grid/80 bg-panel/70 backdrop-blur-xl",
        "shadow-[0_0_30px_rgba(0,0,0,0.18)]",
        glow && "shadow-glow-cyan",
        className
      )}
      {...rest}
    >
      {children}
    </div>
  );
}

/** Section header used at the top of a screen or panel group. */
export function SectionHeader({ eyebrow, title, action, className = "" }) {
  return (
    <div className={cx("flex items-center justify-between gap-3", className)}>
      <div className="flex flex-col leading-tight">
        {eyebrow && (
          <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-muted">
            {eyebrow}
          </span>
        )}
        <h2 className="font-display text-sm font-bold text-text-primary">{title}</h2>
      </div>
      {action}
    </div>
  );
}

/** Small metric card — number + label, used in hero/overview grids. */
export function MetricCard({ label, value, tone = "text-text-primary", icon, sub, className = "" }) {
  return (
    <Panel className={cx("flex flex-col gap-1 p-4", className)}>
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-text-muted">
          {label}
        </span>
        {icon && <span className="text-sm opacity-70">{icon}</span>}
      </div>
      <span className={cx("font-display text-2xl font-bold leading-none", tone)}>{value}</span>
      {sub && <span className="font-mono text-[10px] text-text-muted">{sub}</span>}
    </Panel>
  );
}

const BADGE_TONES = {
  neutral: "border-grid bg-panel-raised text-text-muted",
  gold: "border-gold/40 bg-gold-dim text-gold",
  cyan: "border-cyan/40 bg-cyan-dim text-cyan",
  hp: "border-hp/40 bg-hp-dim text-hp",
  critical: "border-critical/40 bg-critical-dim text-critical",
  ember: "border-ember/40 bg-ember-dim text-ember",
  mana: "border-mana/40 bg-mana-dim text-mana",
};

/** Status/severity chip. */
export function Badge({ tone = "neutral", children, className = "", pulse = false }) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-mono text-[10px] font-medium uppercase tracking-wide",
        BADGE_TONES[tone] || BADGE_TONES.neutral,
        className
      )}
    >
      {pulse && <span className="h-1.5 w-1.5 animate-pulseDot rounded-full bg-current" />}
      {children}
    </span>
  );
}

const BUTTON_VARIANTS = {
  primary: "border-gold/50 bg-gold-dim text-gold hover:bg-gold/20 hover:shadow-glow",
  outline: "border-grid bg-transparent text-text-primary hover:bg-panel-raised",
  ghost: "border-transparent bg-transparent text-text-muted hover:bg-panel-raised hover:text-text-primary",
  critical: "border-critical/50 bg-critical-dim text-critical hover:bg-critical/20 hover:shadow-glow-critical",
  cyan: "border-cyan/50 bg-cyan-dim text-cyan hover:bg-cyan/20 hover:shadow-glow-cyan",
};

/** Command button — visual parity with the newer UI's button system. */
export function Button({ variant = "primary", className = "", children, disabled, ...rest }) {
  return (
    <button
      disabled={disabled}
      className={cx(
        "inline-flex items-center justify-center gap-1.5 rounded-xl border px-4 py-2",
        "font-mono text-xs font-medium tracking-wide transition-all duration-200",
        "disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:shadow-none",
        BUTTON_VARIANTS[variant] || BUTTON_VARIANTS.primary,
        className
      )}
      {...rest}
    >
      {children}
    </button>
  );
}

/** Empty state block — used when a list/panel has no data yet. */
export function EmptyState({ icon = "◌", title, hint, className = "" }) {
  return (
    <div className={cx("flex flex-col items-center justify-center gap-2 py-12 text-center", className)}>
      <span className="text-2xl opacity-40">{icon}</span>
      <span className="font-display text-sm text-text-muted">{title}</span>
      {hint && <span className="max-w-xs font-mono text-[11px] text-text-muted/70">{hint}</span>}
    </div>
  );
}

/** Loading state block. */
export function LoadingState({ label = "Loading…", className = "" }) {
  return (
    <div className={cx("flex flex-col items-center justify-center gap-2 py-12 text-center", className)}>
      <span className="h-2 w-2 animate-pulseDot rounded-full bg-cyan" />
      <span className="font-mono text-[11px] text-text-muted">{label}</span>
    </div>
  );
}
