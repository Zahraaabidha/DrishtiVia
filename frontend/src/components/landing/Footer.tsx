const QUICK_LINKS = [
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'Model Performance', href: '#models' },
  { label: 'Live Dashboard', href: '/dashboard' },
  { label: 'GitHub', href: 'https://github.com/Zahraaabidha/DrishtiVia' },
]

const TECH_STACK = [
  { name: 'YOLOv8s', role: 'Object detection' },
  { name: 'ByteTrack', role: 'Multi-object tracking' },
  { name: 'OpenCV', role: 'Frame processing' },
  { name: 'SQLite', role: 'Evidence archiving' },
  { name: 'React + Vite', role: 'Dashboard UI' },
  { name: 'Python', role: 'Pipeline backend' },
]

const MODEL_STATS = [
  { value: '97.7%', label: 'Wrong-Side mAP50' },
  { value: '91.1%', label: 'Seatbelt mAP50' },
  { value: '78.8%', label: 'Helmet mAP50' },
  { value: '7', label: 'Violation types' },
]

export default function Footer() {
  return (
    <footer
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        width: '100%',
        height: '60vh',
        zIndex: 0,
        backgroundColor: '#0a0a0a',
        color: '#fff',
        fontFamily: 'inherit',
        display: 'flex',
        flexDirection: 'column',
        padding: 'clamp(32px, 3.5vw, 52px) clamp(24px, 6vw, 80px) 0',
        boxSizing: 'border-box',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
          gap: '36px',
          width: '100%',
          flex: 1,
        }}
      >
        {/* Brand */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
            <div style={{ width: '28px', height: '28px', borderRadius: '50%', backgroundColor: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <span style={{ color: '#0a0a0a', fontWeight: 800, fontSize: '8px', letterSpacing: '-0.03em' }}>DV</span>
            </div>
            <span style={{ fontWeight: 700, fontSize: '13px', letterSpacing: '-0.01em' }}>DrishtiVia</span>
          </div>
          <p style={{ fontSize: '11px', color: '#555', lineHeight: '1.8', marginBottom: '10px' }}>
            दृष्टि — Vision. A six-stage AI pipeline for real-time traffic violation detection. Helmet, seatbelt, wrong-side, triple-riding, stop-line, red-light &amp; parking — automated.
          </p>
          <p style={{ fontSize: '10px', color: '#333', letterSpacing: '0.1em', fontWeight: 700 }}>
            FLIPKART GRIDLOCK HACKATHON 2.0
          </p>
        </div>

        {/* Navigate */}
        <div>
          <p style={{ fontSize: '10px', letterSpacing: '0.12em', color: '#444', marginBottom: '14px', fontWeight: 700 }}>NAVIGATE</p>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {QUICK_LINKS.map((l) => (
              <li key={l.label} style={{ marginBottom: '8px' }}>
                <a
                  href={l.href}
                  style={{ color: '#666', textDecoration: 'none', fontSize: '12px', transition: 'color 0.2s' }}
                  onMouseEnter={(e) => ((e.currentTarget as HTMLAnchorElement).style.color = '#fff')}
                  onMouseLeave={(e) => ((e.currentTarget as HTMLAnchorElement).style.color = '#666')}
                >
                  {l.label}
                </a>
              </li>
            ))}
          </ul>
        </div>

        {/* Tech Stack */}
        <div>
          <p style={{ fontSize: '10px', letterSpacing: '0.12em', color: '#444', marginBottom: '14px', fontWeight: 700 }}>TECH STACK</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '7px' }}>
            {TECH_STACK.map((t) => (
              <div key={t.name} style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                <span style={{ fontSize: '12px', color: '#888' }}>{t.name}</span>
                <span style={{ fontSize: '10px', color: '#333' }}>{t.role}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Model accuracy */}
        <div>
          <p style={{ fontSize: '10px', letterSpacing: '0.12em', color: '#444', marginBottom: '14px', fontWeight: 700 }}>MODEL ACCURACY</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {MODEL_STATS.map(({ value, label }) => (
              <div key={label}>
                <p style={{ fontSize: '18px', fontWeight: 700, color: '#fff', lineHeight: 1, letterSpacing: '-0.03em' }}>{value}</p>
                <p style={{ fontSize: '10px', color: '#444', marginTop: '2px' }}>{label}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={{ width: '100%', height: '1px', backgroundColor: '#1e1e1e', flexShrink: 0 }} />

      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', flexShrink: 0, gap: '16px' }}>
        <p
          style={{
            fontSize: 'clamp(48px, 9vw, 120px)',
            fontWeight: 800,
            letterSpacing: '-0.05em',
            lineHeight: 0.82,
            color: '#3a3a3a',
            whiteSpace: 'nowrap',
            userSelect: 'none',
          }}
        >
          DrishtiVia
        </p>

        <div style={{ textAlign: 'right', paddingBottom: '6px', flexShrink: 0 }}>
          <p style={{ fontSize: '13px', fontWeight: 700, color: '#666', letterSpacing: '-0.01em' }}>
            Zahra Aabidha
          </p>
          <p style={{ fontSize: '10px', color: '#333', marginTop: '3px', letterSpacing: '0.06em' }}>
            © 2025 · All rights reserved
          </p>
        </div>
      </div>
    </footer>
  )
}
