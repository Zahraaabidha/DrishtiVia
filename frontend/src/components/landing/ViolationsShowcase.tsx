import { useEffect, useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import './ViolationsShowcase.css'

gsap.registerPlugin(ScrollTrigger)

const PANELS = [
  {
    badge: 'SAFETY GEAR',
    image: '/images/helmet_detect.jpg',
    violations: [
      {
        title: 'Helmet Non-Compliance',
        desc: 'Detects riders on motorcycles without helmets using head-crop classification on every detected rider.',
        stat: 'mAP50 78.8% — Fine-tuned YOLOv8s',
      },
      {
        title: 'Seatbelt Non-Compliance',
        desc: 'Crops the car interior region and classifies the driver seat for seatbelt presence at each frame.',
        stat: 'mAP50 91.1% — Fine-tuned YOLOv8s',
      },
    ],
  },
  {
    badge: 'DIRECTION CONTROL',
    image: '/images/triple_ride.jpeg',
    violations: [
      {
        title: 'Wrong-Side Driving',
        desc: 'Classifies vehicles driving against the permitted flow direction — highest accuracy model in the suite.',
        stat: 'mAP50 97.7% — Fine-tuned YOLOv8s',
      },
      {
        title: 'Triple Riding',
        desc: 'Counts persons paired to each motorcycle via overlap geometry and posture filtering.',
        stat: 'Heuristic — Geometric filter + COCO',
      },
    ],
  },
  {
    badge: 'SIGNAL COMPLIANCE',
    image: '/images/stop_line.webp',
    violations: [
      {
        title: 'Stop-Line Violation',
        desc: 'Tracks vehicle bounding-box bottom edges against a configurable stop-line pixel coordinate.',
        stat: 'Calibrated — Y-threshold crossing',
      },
      {
        title: 'Red-Light Violation',
        desc: 'Combines stop-line crossing with operator-set signal state to flag red-light runners.',
        stat: 'Calibrated — Stop-line + signal flag',
      },
    ],
  },
  {
    badge: 'STATIONARY OFFENCES',
    image: '/images/illegal_parking.jpg',
    violations: [
      {
        title: 'Illegal Parking',
        desc: 'Marks cars as parked when their centroid moves less than 20 px across 60 tracked frames.',
        stat: '< 20 px / 60 frames — ByteTrack history',
      },
    ],
  },
]

const BG_COLORS = ['#f0f0f0', '#ebebeb', '#f2f2f2', '#eee']

export default function ViolationsShowcase() {
  const containerRef = useRef<HTMLDivElement>(null)
  const rightRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const ctx = gsap.context(() => {
      const wrappers = gsap.utils.toArray<HTMLElement>('.vs-img-wrapper')
      wrappers.forEach((el, i) => {
        el.style.zIndex = String(wrappers.length - i)
      })

      const imgs = gsap.utils.toArray<HTMLElement>('.vs-img-wrapper img')
      const panels = gsap.utils.toArray<HTMLElement>('.vs-panel')

      gsap.set(imgs, { clipPath: 'inset(0px 0px 0%)', objectPosition: '50% 60%' })

      ScrollTrigger.matchMedia({
        '(min-width: 769px)': () => {
          ScrollTrigger.create({
            trigger: '.vs-arch',
            start: 'top top',
            end: 'bottom bottom',
            pin: '.vs-arch__right',
          })

          imgs.forEach((img, i) => {
            const panel = panels[i]
            if (!panel) return

            ScrollTrigger.create({
              trigger: panel,
              start: 'top center',
              end: 'bottom center',
              onEnter: () =>
                gsap.to(containerRef.current!, {
                  backgroundColor: BG_COLORS[i],
                  duration: 0.6,
                  ease: 'power2.inOut',
                }),
              onEnterBack: () =>
                gsap.to(containerRef.current!, {
                  backgroundColor: BG_COLORS[i],
                  duration: 0.6,
                  ease: 'power2.inOut',
                }),
            })

            if (i === imgs.length - 1) return

            gsap.to(img, {
              clipPath: 'inset(0px 0px 100%)',
              objectPosition: '50% 30%',
              ease: 'none',
              scrollTrigger: {
                trigger: panel,
                start: 'bottom 85%',
                end: 'bottom top',
                scrub: 1,
              },
            })

            const nextImg = imgs[i + 1]
            if (nextImg) {
              gsap.fromTo(
                nextImg,
                { objectPosition: '50% 65%' },
                {
                  objectPosition: '50% 45%',
                  ease: 'none',
                  scrollTrigger: {
                    trigger: panel,
                    start: 'bottom 85%',
                    end: 'bottom top',
                    scrub: 1,
                  },
                }
              )
            }
          })
        },

        '(max-width: 768px)': () => {
          imgs.forEach((img) => {
            gsap.fromTo(
              img,
              { objectPosition: '50% 60%' },
              {
                objectPosition: '50% 30%',
                ease: 'none',
                scrollTrigger: {
                  trigger: img,
                  start: 'top bottom',
                  end: 'bottom top',
                  scrub: true,
                },
              }
            )
          })
        },
      })
    }, containerRef)

    return () => ctx.revert()
  }, [])

  return (
    <div id="features" ref={containerRef} className="vs-container" style={{ backgroundColor: '#f5f5f5' }}>
      <div className="vs-header">
        <p>03 — VIOLATION DETECTION</p>
        <h2>7 violations caught,<br />every time.</h2>
      </div>

      <div className="vs-arch">
        <div className="vs-arch__left">
          {PANELS.map((panel, pi) => (
            <div key={pi} className="vs-panel">
              <div className="vs-panel__inner">
                <div className="vs-badge">{panel.badge}</div>

                {panel.violations.map((v, vi) => (
                  <div key={vi}>
                    {vi > 0 && <div className="vs-divider" />}
                    <div className="vs-violation">
                      <h3>{v.title}</h3>
                      <p>{v.desc}</p>
                      <p className="vs-stat">{v.stat}</p>
                    </div>
                  </div>
                ))}

                <a className="vs-link" href="/dashboard">
                  <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" fill="none">
                    <path fill="#121212" d="M5 2c0 1.105-1.895 2-3 2a2 2 0 1 1 0-4c1.105 0 3 .895 3 2ZM11 3.5c0 1.105-.895 3-2 3s-2-1.895-2-3a2 2 0 1 1 4 0ZM6 9a2 2 0 1 1-4 0c0-1.105.895-3 2-3s2 1.895 2 3Z" />
                  </svg>
                  <span>View in Dashboard</span>
                </a>
              </div>
            </div>
          ))}
        </div>

        <div ref={rightRef} className="vs-arch__right">
          {PANELS.map((panel, i) => (
            <div key={i} className="vs-img-wrapper" data-index={i + 1}>
              <img src={panel.image} alt={panel.badge} />
            </div>
          ))}
        </div>
      </div>

      <div className="vs-spacer" />
    </div>
  )
}
