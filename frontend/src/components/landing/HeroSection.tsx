import { useState, useEffect, useRef } from 'react'
import { ArrowRight, Clock, Menu, X } from 'lucide-react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

function useBengaluruTime() {
  const [time, setTime] = useState('')
  useEffect(() => {
    const update = () => {
      const t = new Date().toLocaleTimeString('en-IN', {
        timeZone: 'Asia/Kolkata',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      })
      setTime(t)
    }
    update()
    const id = setInterval(update, 1000)
    return () => clearInterval(id)
  }, [])
  return time
}

const HackathonBadge = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" className="w-5 h-5 sm:w-6 sm:h-6 fill-current text-[#E8704E] flex-shrink-0">
    <path d="m19.6 66.5 19.7-11 .3-1-.3-.5h-1l-3.3-.2-11.2-.3L14 53l-9.5-.5-2.4-.5L0 49l.2-1.5 2-1.3 2.9.2 6.3.5 9.5.6 6.9.4L38 49.1h1.6l.2-.7-.5-.4-.4-.4L29 41l-10.6-7-5.6-4.1-3-2-1.5-2-.6-4.2 2.7-3 3.7.3.9.2 3.7 2.9 8 6.1L37 36l1.5 1.2.6-.4.1-.3-.7-1.1L33 25l-6-10.4-2.7-4.3-.7-2.6c-.3-1-.4-2-.4-3l3-4.2L28 0l4.2.6L33.8 2l2.6 6 4.1 9.3L47 29.9l2 3.8 1 3.4.3 1h.7v-.5l.5-7.2 1-8.7 1-11.2.3-3.2 1.6-3.8 3-2L61 2.6l2 2.9-.3 1.8-1.1 7.7L59 27.1l-1.5 8.2h.9l1-1.1 4.1-5.4 6.9-8.6 3-3.5L77 13l2.3-1.8h4.3l3.1 4.7-1.4 4.9-4.4 5.6-3.7 4.7-5.3 7.1-3.2 5.7.3.4h.7l12-2.6 6.4-1.1 7.6-1.3 3.5 1.6.4 1.6-1.4 3.4-8.2 2-9.6 2-14.3 3.3-.2.1.2.3 6.4.6 2.8.2h6.8l12.6 1 3.3 2 1.9 2.7-.3 2-5.1 2.6-6.8-1.6-16-3.8-5.4-1.3h-.8v.4l4.6 4.5 8.3 7.5L89 80.1l.5 2.4-1.3 2-1.4-.2-9.2-7-3.6-3-8-6.8h-.5v.7l1.8 2.7 9.8 14.7.5 4.5-.7 1.4-2.6 1-2.7-.6-5.8-8-6-9-4.7-8.2-.5.4-2.9 30.2-1.3 1.5-3 1.2-2.5-2-1.4-3 1.4-6.2 1.6-8 1.3-6.4 1.2-7.9.7-2.6v-.2H49L43 72l-9 12.3-7.2 7.6-1.7.7-3-1.5.3-2.8L24 86l10-12.8 6-7.9 4-4.6-.1-.5h-.3L17.2 77.4l-4.7.6-2-2 .2-3 1-1 8-5.5Z"/>
  </svg>
)

const NAV_LINKS = ['Features', 'Models', 'How It Works', 'GitHub']

export default function HeroSection() {
  const time = useBengaluruTime()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const labelRef = useRef<HTMLParagraphElement>(null)
  const headlineRef = useRef<HTMLHeadingElement>(null)
  const ctaRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const tl = gsap.timeline({ delay: 0.2 })

    if (labelRef.current) {
      tl.fromTo(labelRef.current,
        { opacity: 0, y: 16 },
        { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' }
      )
    }

    if (headlineRef.current) {
      const lines = headlineRef.current.querySelectorAll('.gsap-line')
      tl.fromTo(lines,
        { opacity: 0, y: 30 },
        { opacity: 1, y: 0, duration: 0.8, stagger: 0.1, ease: 'power3.out' },
        '-=0.3'
      )
    }

    if (ctaRef.current) {
      tl.fromTo(ctaRef.current,
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' },
        '-=0.4'
      )
    }

    const heroEl = document.querySelector('.hero-section') as HTMLElement
    const videoEl = document.querySelector('.hero-video') as HTMLElement

    if (heroEl && videoEl) {
      gsap.to(videoEl, {
        scrollTrigger: {
          trigger: heroEl,
          start: 'top top',
          end: 'bottom top',
          scrub: true,
        },
        y: '-30%',
        ease: 'none',
      })
    }
  }, [])

  return (
    <section className="hero-section relative min-h-screen flex flex-col" style={{ backgroundColor: '#111', overflow: 'hidden' }}>
      {/* Video background */}
      <video
        className="hero-video absolute inset-0 w-full object-cover z-0"
        style={{ top: '-20%', height: '150%' }}
        src="/videos/hero_bg.mp4"
        autoPlay
        loop
        muted
        playsInline
      />

      {/* Navbar */}
      <nav className="relative z-20 px-2 sm:px-3 pt-2 sm:pt-3">
        <div className="max-w-[1440px] mx-auto">
          <div className="bg-white rounded-full p-[5px] flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div className="w-9 h-9 sm:w-10 sm:h-10 bg-gray-900 rounded-full flex items-center justify-center flex-shrink-0">
                <span className="text-white font-bold tracking-tight" style={{ fontSize: '10px' }}>DV</span>
              </div>
              <div className="hidden md:flex items-center gap-6">
                {NAV_LINKS.map((link) => (
                  <a
                    key={link}
                    href={link === 'GitHub' ? 'https://github.com/Zahraaabidha/DrishtiVia' : `#${link.toLowerCase().replace(/\s+/g, '-')}`}
                    target={link === 'GitHub' ? '_blank' : undefined}
                    rel={link === 'GitHub' ? 'noopener noreferrer' : undefined}
                    className="text-gray-900 hover:text-gray-500 transition-colors duration-300"
                    style={{ fontSize: '14px' }}
                  >
                    {link}
                  </a>
                ))}
              </div>
            </div>

            <div className="hidden md:flex items-center gap-4">
              <span className="hidden lg:block text-gray-600" style={{ fontSize: '13px' }}>
                Flipkart Gridlock Hackathon 2.0
              </span>
              <div className="flex items-center gap-1.5 text-gray-600">
                <Clock size={14} />
                <span style={{ fontSize: '13px' }}>{time} IST · Bengaluru</span>
              </div>
              <a
                href="/dashboard"
                className="group bg-gray-900 text-white rounded-full pl-5 pr-2 py-2 flex items-center gap-3 overflow-hidden no-underline"
                style={{ fontSize: '13px', fontWeight: '500' }}
              >
                <div className="overflow-hidden" style={{ height: '20px' }}>
                  <div className="flex flex-col transition-transform duration-500" style={{ transitionTimingFunction: 'cubic-bezier(0.25,0.1,0.25,1)' }}>
                    <span className="group-hover:-translate-y-full transition-transform duration-500" style={{ transitionTimingFunction: 'cubic-bezier(0.25,0.1,0.25,1)', lineHeight: '20px', display: 'block' }}>
                      Open Dashboard
                    </span>
                    <span className="group-hover:-translate-y-full transition-transform duration-500" style={{ transitionTimingFunction: 'cubic-bezier(0.25,0.1,0.25,1)', lineHeight: '20px', display: 'block' }}>
                      Open Dashboard
                    </span>
                  </div>
                </div>
                <div className="w-6 h-6 bg-white rounded-full flex items-center justify-center flex-shrink-0 transition-transform duration-500 group-hover:-rotate-45" style={{ transitionTimingFunction: 'cubic-bezier(0.25,0.1,0.25,1)' }}>
                  <ArrowRight size={12} className="text-gray-900" />
                </div>
              </a>
            </div>

            <button
              className="md:hidden bg-gray-900 rounded-full p-2 flex items-center justify-center"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? <X size={18} className="text-white" /> : <Menu size={18} className="text-white" />}
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile menu overlay */}
      <div
        className={`fixed inset-0 z-50 md:hidden transition-opacity duration-300 ${mobileMenuOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}`}
        style={{ backgroundColor: 'rgba(0,0,0,0.6)' }}
        onClick={() => setMobileMenuOpen(false)}
      >
        <div
          className={`absolute bottom-0 left-0 right-0 mx-3 mb-3 bg-white rounded-2xl p-6 transition-transform duration-500 ${mobileMenuOpen ? 'translate-y-0' : 'translate-y-full'}`}
          style={{ transitionTimingFunction: 'cubic-bezier(0.32,0.72,0,1)' }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center gap-1.5 text-gray-600 mb-6 text-sm">
            <Clock size={14} />
            <span>{time} IST · Bengaluru</span>
          </div>
          <div className="flex flex-col gap-4 mb-8">
            {NAV_LINKS.map((link) => (
              <a
                key={link}
                href={link === 'GitHub' ? 'https://github.com/Zahraaabidha/DrishtiVia' : `#${link.toLowerCase().replace(/\s+/g, '-')}`}
                className="text-gray-900 font-medium"
                style={{ fontSize: '28px', lineHeight: '32px' }}
                onClick={() => setMobileMenuOpen(false)}
              >
                {link}
              </a>
            ))}
          </div>
          <a
            href="/dashboard"
            className="group bg-gray-900 text-white rounded-full pl-5 pr-2 py-2 flex items-center gap-3 w-full justify-between no-underline"
          >
            <span style={{ fontSize: '14px', fontWeight: '500' }}>Open Dashboard</span>
            <div className="w-7 h-7 bg-white rounded-full flex items-center justify-center flex-shrink-0 transition-transform duration-500 group-hover:-rotate-45" style={{ transitionTimingFunction: 'cubic-bezier(0.25,0.1,0.25,1)' }}>
              <ArrowRight size={14} className="text-gray-900" />
            </div>
          </a>
        </div>
      </div>

      {/* Hero content */}
      <div className="relative z-20 flex-1 flex flex-col">
        <div className="flex-1" />
        <div className="max-w-[1440px] mx-auto w-full px-5 sm:px-8 lg:px-12 pb-14 sm:pb-16 lg:pb-20">
          <p ref={labelRef} className="text-white/70 tracking-wide mb-5 sm:mb-8" style={{ fontSize: '13px', lineHeight: '14px', opacity: 0 }}>
            DrishtiVia · दृष्टि — Vision
          </p>

          <h1
            ref={headlineRef}
            className="font-medium text-white mb-0"
            style={{
              fontSize: 'clamp(1.75rem, 7vw, 4.2rem)',
              lineHeight: '1.08',
              letterSpacing: '-0.03em',
            }}
          >
            <span className="sm:hidden gsap-line block" style={{ opacity: 0 }}>AI that catches traffic violations before they become road fatalities.</span>
            <span className="hidden sm:block" style={{ fontSize: 'clamp(2.5rem, 5vw, 4.2rem)' }}>
              <span className="gsap-line block overflow-hidden" style={{ opacity: 0 }}>AI that catches traffic</span>
              <span className="gsap-line block overflow-hidden" style={{ opacity: 0 }}>violations before they</span>
              <span className="gsap-line block overflow-hidden" style={{ opacity: 0 }}>become road fatalities.</span>
            </span>
          </h1>

          <div ref={ctaRef} className="mt-8 sm:mt-12 flex flex-col sm:flex-row gap-4 sm:gap-5 items-start" style={{ opacity: 0 }}>
            <a
              href="/dashboard"
              className="group flex items-center gap-3 rounded-full pl-5 sm:pl-6 pr-2 py-2 overflow-hidden text-white no-underline"
              style={{ backgroundColor: '#F26522', fontSize: '13px', lineHeight: '14px' }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#e05a1a')}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#F26522')}
            >
              <div className="overflow-hidden" style={{ height: '20px' }}>
                <div className="flex flex-col">
                  <span className="group-hover:-translate-y-full transition-transform duration-500 block" style={{ transitionTimingFunction: 'cubic-bezier(0.25,0.1,0.25,1)', lineHeight: '20px' }}>
                    Try Live Detection
                  </span>
                  <span className="group-hover:-translate-y-full transition-transform duration-500 block" style={{ transitionTimingFunction: 'cubic-bezier(0.25,0.1,0.25,1)', lineHeight: '20px' }}>
                    Try Live Detection
                  </span>
                </div>
              </div>
              <div className="w-7 h-7 sm:w-8 sm:h-8 bg-white rounded-full flex items-center justify-center flex-shrink-0 transition-transform duration-500 group-hover:-rotate-45" style={{ transitionTimingFunction: 'cubic-bezier(0.25,0.1,0.25,1)' }}>
                <ArrowRight size={14} style={{ color: '#F26522' }} />
              </div>
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}
