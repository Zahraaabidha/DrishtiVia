import { useEffect, useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

const WORDS = [
  'From', 'raw', 'footage,', 'every', 'violation',
  'is', 'caught,', 'confirmed,', 'and', 'filed',
  '—', 'automatically.',
]

export default function PinnedTextReveal() {
  const outerRef = useRef<HTMLDivElement>(null)
  const wrapRef  = useRef<HTMLDivElement>(null)
  const wordsRef = useRef<HTMLSpanElement[]>([])

  useEffect(() => {
    const ctx = gsap.context(() => {
      if (!wrapRef.current || !outerRef.current) return

      const scrollDist = WORDS.length * 120

      gsap.set(outerRef.current, { minHeight: `calc(100vh + ${scrollDist}px)` })

      gsap.fromTo(
        wordsRef.current,
        { color: '#2a2a2a' },
        {
          color: '#ffffff',
          stagger: 0.8,
          ease: 'none',
          scrollTrigger: {
            trigger: wrapRef.current,
            start: 'top top',
            end: `+=${scrollDist}`,
            scrub: 1.5,
            pin: true,
            anticipatePin: 1,
          },
        }
      )
    })

    return () => ctx.revert()
  }, [])

  return (
    <div
      ref={outerRef}
      style={{
        backgroundColor: '#0a0a0a',
        position: 'relative',
        zIndex: 10,
      }}
    >
      <div
        ref={wrapRef}
        style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
          justifyContent: 'center',
          padding: '0 clamp(24px, 8vw, 120px)',
          backgroundColor: '#0a0a0a',
        }}
      >
        <div style={{ maxWidth: '1100px', width: '100%' }}>
          <p
            style={{
              fontSize: 'clamp(2rem, 5.2vw, 4.8rem)',
              fontWeight: 700,
              lineHeight: 1.2,
              letterSpacing: '-0.03em',
            }}
          >
            {WORDS.map((word, i) => (
              <span
                key={i}
                ref={(el) => { if (el) wordsRef.current[i] = el }}
                style={{ display: 'inline', color: '#2a2a2a' }}
              >
                {word}{' '}
              </span>
            ))}
          </p>

          <p
            style={{
              marginTop: '40px',
              fontSize: '11px',
              letterSpacing: '0.14em',
              color: '#333',
              fontWeight: 600,
            }}
          >
            DRISHTAVIA · दृष्टि — VISION · BENGALURU TRAFFIC AI
          </p>
        </div>
      </div>
    </div>
  )
}
