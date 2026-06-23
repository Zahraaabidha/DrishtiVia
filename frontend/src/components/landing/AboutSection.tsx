import { useState, useEffect, useRef } from 'react'
import { ArrowRight } from 'lucide-react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

function OrangeButton({ label, href = '#' }: { label: string; href?: string }) {
  return (
    <a
      href={href}
      className="group flex items-center gap-3 rounded-full pl-5 sm:pl-6 pr-2 py-2 overflow-hidden text-white flex-shrink-0 no-underline"
      style={{ backgroundColor: '#F26522', fontSize: '13px', lineHeight: '14px' }}
      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#e05a1a')}
      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#F26522')}
    >
      <div className="overflow-hidden" style={{ height: '20px' }}>
        <div className="flex flex-col">
          <span className="group-hover:-translate-y-full transition-transform duration-500 block" style={{ transitionTimingFunction: 'cubic-bezier(0.25,0.1,0.25,1)', lineHeight: '20px' }}>
            {label}
          </span>
          <span className="group-hover:-translate-y-full transition-transform duration-500 block" style={{ transitionTimingFunction: 'cubic-bezier(0.25,0.1,0.25,1)', lineHeight: '20px' }}>
            {label}
          </span>
        </div>
      </div>
      <div
        className="w-7 h-7 sm:w-8 sm:h-8 bg-white rounded-full flex items-center justify-center flex-shrink-0 transition-transform duration-500 group-hover:-rotate-45"
        style={{ transitionTimingFunction: 'cubic-bezier(0.25,0.1,0.25,1)' }}
      >
        <ArrowRight size={14} style={{ color: '#F26522' }} />
      </div>
    </a>
  )
}

const PIPELINE_STEPS = [
  {
    step: '01',
    label: 'PREPROCESS',
    heading: 'Raw footage is cleaned and enhanced for analysis.',
    detail: 'CLAHE + dark-channel dehazing for fog, dust & night footage',
  },
  {
    step: '02',
    label: 'DETECT',
    heading: 'Every vehicle and person in frame is identified.',
    detail: 'YOLOv8s COCO model identifies all vehicles and persons in each frame.',
  },
  {
    step: '03',
    label: 'TRACK',
    heading: 'Stable identities are assigned across all frames.',
    detail: 'ByteTrack assigns stable V-01, V-02 … IDs across frames for consistent tracking.',
  },
  {
    step: '04',
    label: 'CLASSIFY',
    heading: 'Three specialized models check each violation type.',
    detail: '3 fine-tuned models check helmet, seatbelt & wrong-side compliance per vehicle.',
  },
  {
    step: '05',
    label: 'CONFIRM',
    heading: 'A temporal filter eliminates false positives.',
    detail: '2-sighting temporal filter must trigger before a violation is raised.',
  },
  {
    step: '06',
    label: 'ALERT',
    heading: 'Evidence is archived automatically for review.',
    detail: 'Evidence saved to SQLite with snapshot, plate & severity — ready for filing.',
  },
]

export default function AboutSection() {
  const [active, setActive] = useState(0)
  const sectionRef = useRef<HTMLElement>(null)
  const timelineRef = useRef<HTMLDivElement>(null)

  const prev = () => setActive((i) => (i === 0 ? PIPELINE_STEPS.length - 1 : i - 1))
  const next = () => setActive((i) => (i === PIPELINE_STEPS.length - 1 ? 0 : i + 1))

  const current = PIPELINE_STEPS[active]

  useEffect(() => {
    const ctx = gsap.context(() => {
      if (timelineRef.current) {
        gsap.fromTo(
          timelineRef.current,
          { opacity: 0, y: 40 },
          {
            opacity: 1,
            y: 0,
            duration: 1.1,
            ease: 'power3.out',
            scrollTrigger: {
              trigger: timelineRef.current,
              start: 'top 85%',
              toggleActions: 'play none none none',
            },
          }
        )
      }
    }, sectionRef)

    return () => ctx.revert()
  }, [])

  return (
    <section ref={sectionRef} id="how-it-works" className="bg-white pt-16 sm:pt-20 lg:pt-32 pb-12 sm:pb-16 lg:pb-24 overflow-hidden">
      <div className="max-w-[1440px] mx-auto px-5 sm:px-8 lg:px-12">

        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-10 lg:gap-20 mb-16 sm:mb-20 lg:mb-24">
          <div className="flex-shrink-0">
            <h2
              className="font-medium text-gray-900 mb-8 lg:mb-10"
              style={{
                fontSize: 'clamp(2rem, 5vw, 3.8rem)',
                lineHeight: '1.08',
                letterSpacing: '-0.03em',
              }}
            >
              Six-stage AI pipeline,<br />
              from raw footage<br />
              to filed evidence.
            </h2>

            <div className="flex items-center gap-4">
              <button
                onClick={prev}
                className="w-10 h-10 rounded-full border border-gray-300 flex items-center justify-center text-gray-500 hover:border-gray-900 hover:text-gray-900 transition-colors duration-200"
                aria-label="Previous step"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M15 18l-6-6 6-6" />
                </svg>
              </button>
              <button
                onClick={next}
                className="w-10 h-10 rounded-full border border-gray-900 flex items-center justify-center text-gray-900 hover:bg-gray-900 hover:text-white transition-colors duration-200"
                aria-label="Next step"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 18l6-6-6-6" />
                </svg>
              </button>
            </div>
          </div>

          <div className="lg:max-w-lg xl:max-w-xl lg:text-right">
            <p
              key={active}
              className="font-semibold text-gray-900"
              style={{
                fontSize: 'clamp(1.4rem, 3vw, 2.4rem)',
                lineHeight: '1.25',
                letterSpacing: '-0.02em',
                animation: 'stepFade 0.35s ease',
              }}
            >
              {current.heading.split(' ').map((word, i, arr) => {
                const fade = i >= arr.length - 3
                return (
                  <span key={i} style={{ color: fade ? '#c0c0c0' : '#111111' }}>
                    {word}{i < arr.length - 1 ? ' ' : ''}
                  </span>
                )
              })}
            </p>
            <p
              key={active + '-detail'}
              className="text-gray-400 mt-4"
              style={{ fontSize: '14px', lineHeight: '1.65', animation: 'stepFade 0.4s ease' }}
            >
              {current.detail}
            </p>
          </div>
        </div>

        <div ref={timelineRef} className="mb-16 sm:mb-20">
          <div className="relative flex items-center justify-between mb-5">
            <div className="absolute left-0 right-0 bg-gray-200" style={{ top: '50%', transform: 'translateY(-50%)', height: '1.5px' }} />
            {PIPELINE_STEPS.map((s, i) => (
              <button
                key={s.step}
                onClick={() => setActive(i)}
                className="relative z-10 flex-shrink-0 transition-all duration-300"
                aria-label={s.label}
              >
                <div
                  className="rounded-full transition-all duration-300"
                  style={{
                    width: i === active ? '28px' : '13px',
                    height: i === active ? '28px' : '13px',
                    backgroundColor: i === active ? '#7c3aed' : '#d1d5db',
                  }}
                />
              </button>
            ))}
          </div>

          <div className="flex items-start justify-between">
            {PIPELINE_STEPS.map((s, i) => (
              <button
                key={s.step}
                onClick={() => setActive(i)}
                className="flex-shrink-0 text-center transition-colors duration-200"
                style={{
                  fontSize: '11px',
                  letterSpacing: '0.09em',
                  fontWeight: i === active ? 700 : 400,
                  color: i === active ? '#111111' : '#9ca3af',
                  width: `${100 / PIPELINE_STEPS.length}%`,
                }}
              >
                {s.label}
              </button>
            ))}
          </div>

          <div className="mt-7 flex items-start gap-5">
            <span className="text-gray-300 font-semibold flex-shrink-0" style={{ fontSize: '15px', letterSpacing: '0.06em' }}>
              {current.step}
            </span>
            <p className="text-gray-700 font-medium" style={{ fontSize: '15px', lineHeight: '1.65' }}>
              {current.label.charAt(0) + current.label.slice(1).toLowerCase()} — {current.detail}
            </p>
          </div>
        </div>

        <div className="flex flex-col lg:flex-row items-start lg:items-end gap-10 lg:gap-0 justify-between">
          <div className="flex flex-col items-start lg:items-end gap-5 w-full lg:text-right">
            <p className="font-medium text-gray-900" style={{ fontSize: '15px', lineHeight: '1.65' }}>
              Real-time detection, temporal confirmation, and automatic evidence archiving — built for Bengaluru traffic.
            </p>
            <OrangeButton label="View model performance" href="/models" />
          </div>
        </div>
      </div>

      <style>{`
        @keyframes stepFade {
          from { opacity: 0; transform: translateY(6px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </section>
  )
}
