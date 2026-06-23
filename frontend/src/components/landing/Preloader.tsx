import { useLayoutEffect, useRef } from 'react'
import gsap from 'gsap'
import { SplitText } from 'gsap/SplitText'
import { CustomEase } from 'gsap/all'

gsap.registerPlugin(SplitText, CustomEase)

// Six decorative image slots — drop traffic/violation JPGs in public/ as
// preloader1.jpg … preloader6.jpg to fill them, or leave as tinted fallbacks.
const IMAGES = [
  '/preloader1.jpg',
  '/preloader2.jpg',
  '/preloader3.jpg',
  '/preloader4.jpg',
  '/preloader5.jpg',
  '/preloader6.jpg',
]

const ROTATIONS = [7.5, -2.5, -10, 12.5, -5, 5]

// Tinted fallback colours shown when image files are missing
const FALLBACK_BG = [
  '#1a1a1a', '#222', '#1c1c1c', '#181818', '#202020', '#1e1e1e',
]

interface Props {
  /** Called when the hero should start sliding up from below (~4.0 s in) */
  onReveal: () => void
  /** Called when the preloader has fully faded out */
  onComplete: () => void
}

export default function Preloader({ onReveal, onComplete }: Props) {
  const rootRef = useRef<HTMLDivElement>(null)

  useLayoutEffect(() => {
    CustomEase.create('hop',  '0.8, 0, 0.2, 1')
    CustomEase.create('hop2', '0.9, 0, 0.1, 1')

    const ctx = gsap.context(() => {
      const heading = rootRef.current?.querySelector<HTMLElement>('.pl-heading')
      if (!heading) return

      const split = SplitText.create(heading, {
        type: 'chars',
        charsClass: 'pl-char',
        mask: 'chars',
      })

      // Initial states
      gsap.set('.pl-char',      { y: '100%' })
      gsap.set('.pl-counter-p', { y: '100%' })
      gsap.set('.pl-img',       { rotate: (i: number) => ROTATIONS[i] })

      const tl = gsap.timeline({ delay: 0.3 })

      // ── Images reveal ──────────────────────────────────────────────────────
      tl.to('.pl-img', {
        scale: 1,
        clipPath: 'polygon(0% 0%, 100% 0%, 100% 100%, 0% 100%)',
        duration: 1,
        ease: 'hop',
        stagger: 0.2,
      })

      // ── Heading chars in ───────────────────────────────────────────────────
      tl.to('.pl-char', {
        y: '0%',
        duration: 1,
        ease: 'hop2',
        stagger: { each: 0.125, from: 'random' },
      }, '0.35')

      // ── Counter slide in + count 000→100 ───────────────────────────────────
      tl.to('.pl-counter-p', {
        y: '0%',
        duration: 1,
        ease: 'hop2',
        onStart() {
          const el = rootRef.current?.querySelector<HTMLElement>('.pl-counter-p')
          if (!el) return
          const obj = { val: 0 }
          gsap.to(obj, {
            val: 100,
            duration: 2,
            delay: 0.5,
            ease: 'power2.inOut',
            onUpdate() {
              el.textContent = String(Math.round(obj.val)).padStart(3, '0')
            },
          })
        },
      }, '<')

      // ── Counter + chars exit ───────────────────────────────────────────────
      tl.to('.pl-counter-p', { y: '-100%', duration: 0.75, ease: 'hop2' }, 3.25)

      tl.to('.pl-char', {
        y: '-100%',
        duration: 0.75,
        ease: 'hop2',
        stagger: { each: 0.125, from: 'random' },
      }, 3.25)

      // ── Images collapse ────────────────────────────────────────────────────
      tl.to('.pl-img', {
        scale: 0,
        clipPath: 'polygon(20% 20%, 80% 20%, 80% 80%, 20% 80%)',
        duration: 1,
        ease: 'hop2',
        stagger: -0.075,
      }, 3.5)

      // ── Trigger hero slide-up from below while preloader is still visible ───
      tl.call(onReveal, [], 4.0)

      // ── Preloader fades out (reference: pt-page-fade outClass) ───────────
      tl.to('.pl-overlay', {
        opacity: 0,
        duration: 0.9,
        ease: 'power2.inOut',
        onComplete,
      }, 4.5)

      return () => split.revert()
    }, rootRef)

    return () => ctx.revert()
  }, [])

  return (
    <div
      ref={rootRef}
      className="pl-overlay"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 100,
        background: '#141414',
        color: '#fff',
        overflow: 'hidden',
        willChange: 'opacity',
      }}
    >
      {/* ── Decorative images ── */}
      <div style={{ position: 'absolute', inset: 0 }}>
        {IMAGES.map((src, i) => (
          <div
            key={i}
            className="pl-img"
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%) scale(0)',
              width: 220,
              height: 280,
              transformOrigin: 'center center',
              clipPath: 'polygon(20% 20%, 80% 20%, 80% 80%, 20% 80%)',
              willChange: 'transform, clip-path',
              background: FALLBACK_BG[i],
              overflow: 'hidden',
            }}
          >
            <img
              src={src}
              alt=""
              style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
            />
          </div>
        ))}
      </div>

      {/* ── Heading + counter ── */}
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        whiteSpace: 'nowrap',
      }}>
        <h1
          className="pl-heading"
          style={{
            fontFamily: "'PP Neue Montreal', 'Inter', sans-serif",
            fontWeight: 500,
            textTransform: 'uppercase',
            fontSize: 'clamp(2rem, 10vw, 13rem)',
            lineHeight: 0.85,
            letterSpacing: '-0.03em',
            color: '#fff',
          }}
        >
          DrishtiVia
        </h1>

        {/* Counter — positioned top-right of the heading */}
        <div style={{
          position: 'absolute',
          top: '-1.5rem',
          left: 'calc(100% + 1.5rem)',
          overflow: 'hidden',
        }}>
          <p
            className="pl-counter-p"
            style={{
              fontFamily: "'PP Neue Montreal', 'Inter', sans-serif",
              fontWeight: 500,
              fontSize: 'clamp(0.9rem, 1.5vw, 1.8rem)',
              lineHeight: 0.85,
              color: '#fff',
              transform: 'translateY(100%)',
              willChange: 'transform',
            }}
          >
            000
          </p>
        </div>
      </div>
    </div>
  )
}
