import { useEffect, useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

const STAT_CARDS = [
  {
    num: '01',
    title: 'Wrong-Side\nDetection',
    value: '97.7%',
    label: 'mAP50',
    detail: 'Classifies vehicles driving against permitted flow direction — highest accuracy model in the suite.',
  },
  {
    num: '02',
    title: 'Seatbelt\nCompliance',
    value: '91.1%',
    label: 'mAP50',
    detail: 'Crops the car interior and classifies the driver seat for seatbelt presence at each frame.',
  },
  {
    num: '03',
    title: 'Helmet\nDetection',
    value: '78.8%',
    label: 'mAP50',
    detail: 'Detects riders on motorcycles without helmets using head-crop classification on every rider.',
  },
  {
    num: '04',
    title: 'Violation\nTypes',
    value: '7',
    label: 'Total',
    detail: 'Helmet, seatbelt, wrong-side, triple riding, stop-line, red-light, and illegal parking violations.',
  },
]

export default function CaseStudiesSection() {
  const sectionRef = useRef<HTMLElement>(null)
  const headerRef = useRef<HTMLDivElement>(null)
  const cardsRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const ctx = gsap.context(() => {
      if (headerRef.current) {
        const subtitle = headerRef.current.querySelector('.gsap-subtitle')
        const heading = headerRef.current.querySelector('.gsap-heading')

        if (subtitle) {
          gsap.fromTo(subtitle,
            { opacity: 0, x: -20 },
            {
              opacity: 1, x: 0, duration: 0.7, ease: 'power2.out',
              scrollTrigger: { trigger: headerRef.current, start: 'top 85%', toggleActions: 'play none none none' },
            }
          )
        }

        if (heading) {
          gsap.fromTo(heading,
            { opacity: 0, y: 40 },
            {
              opacity: 1, y: 0, duration: 0.9, ease: 'power3.out',
              scrollTrigger: { trigger: headerRef.current, start: 'top 85%', toggleActions: 'play none none none' },
            }
          )
        }
      }

      if (cardsRef.current) {
        const cards = cardsRef.current.querySelectorAll('.gsap-card')
        gsap.fromTo(
          cards,
          { opacity: 0, y: 50, scale: 0.97 },
          {
            opacity: 1,
            y: 0,
            scale: 1,
            duration: 0.75,
            stagger: 0.12,
            ease: 'power3.out',
            scrollTrigger: {
              trigger: cardsRef.current,
              start: 'top 88%',
              toggleActions: 'play none none none',
            },
          }
        )
      }
    }, sectionRef)

    return () => ctx.revert()
  }, [])

  return (
    <section ref={sectionRef} id="models" className="pt-16 sm:pt-20 lg:pt-28 pb-16 sm:pb-20 lg:pb-28 bg-white">
      <div className="max-w-[1440px] mx-auto px-5 sm:px-8 lg:px-12">

        <div ref={headerRef} className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-12 sm:mb-16 lg:mb-20">
          <p className="gsap-subtitle text-gray-400" style={{ fontSize: '13px' }}>Built for traffic enforcement</p>
          <h2
            className="gsap-heading font-medium text-gray-900"
            style={{
              fontSize: 'clamp(2.4rem, 6vw, 5rem)',
              lineHeight: '1.0',
              letterSpacing: '-0.03em',
            }}
          >
            Model Performance
          </h2>
        </div>

        <div ref={cardsRef} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 sm:gap-6">
          {STAT_CARDS.map((card) => (
            <div
              key={card.num}
              className="gsap-card group rounded-2xl p-6 sm:p-7 flex flex-col justify-between cursor-pointer transition-all duration-300 hover:shadow-lg"
              style={{ backgroundColor: '#F5F5F5', minHeight: '340px' }}
              onMouseEnter={(e) => ((e.currentTarget as HTMLDivElement).style.backgroundColor = '#eeeeee')}
              onMouseLeave={(e) => ((e.currentTarget as HTMLDivElement).style.backgroundColor = '#F5F5F5')}
            >
              <div className="flex items-start justify-between">
                <span
                  className="rounded-full px-3 py-1 border border-gray-300 text-gray-500 font-medium"
                  style={{ fontSize: '11px', letterSpacing: '0.06em' }}
                >
                  PERFORMANCE
                </span>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 5v14M5 12l7 7 7-7" />
                </svg>
              </div>

              <div className="mt-6">
                <h3
                  className="font-semibold text-gray-900"
                  style={{ fontSize: 'clamp(1.1rem, 2vw, 1.35rem)', lineHeight: '1.25', letterSpacing: '-0.01em', whiteSpace: 'pre-line' }}
                >
                  {card.title}
                </h3>
              </div>

              <div className="mt-auto pt-6">
                <p
                  className="font-bold text-gray-900"
                  style={{ fontSize: 'clamp(3rem, 6vw, 5rem)', lineHeight: '1', letterSpacing: '-0.04em' }}
                >
                  {card.value}
                </p>
                <p className="text-gray-400 mt-1" style={{ fontSize: '12px', letterSpacing: '0.04em' }}>{card.label}</p>
              </div>

              <div className="mt-6 flex items-center justify-between">
                <button
                  className="flex items-center gap-1.5 rounded-full border border-gray-300 px-3 py-1.5 text-gray-500 hover:border-gray-500 hover:text-gray-700 transition-colors duration-200"
                  style={{ fontSize: '11px', letterSpacing: '0.06em' }}
                >
                  <span>+</span>
                  <span>EXPLORE</span>
                </button>
                <span
                  className="text-gray-300 font-bold"
                  style={{ fontSize: 'clamp(1.8rem, 3vw, 2.5rem)', letterSpacing: '-0.04em', lineHeight: '1' }}
                >
                  {card.num}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
