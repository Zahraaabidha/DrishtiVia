import { useLayoutEffect } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import HeroSection from '../components/landing/HeroSection'
import PinnedTextReveal from '../components/landing/PinnedTextReveal'
import AboutSection from '../components/landing/AboutSection'
import ViolationsShowcase from '../components/landing/ViolationsShowcase'
import CaseStudiesSection from '../components/landing/CaseStudiesSection'
import Footer from '../components/landing/Footer'

gsap.registerPlugin(ScrollTrigger)

export default function LandingPage() {
  useLayoutEffect(() => {
    window.scrollTo(0, 0)
    ScrollTrigger.refresh()
  }, [])

  return (
    <div style={{ position: 'relative', backgroundColor: '#0a0a0a' }}>
      {/* Footer is fixed behind content; paddingBottom on content reveals it */}
      <Footer />

      <div style={{ position: 'relative', zIndex: 1, paddingBottom: '60vh' }}>
        <HeroSection animReady={true} />
        <PinnedTextReveal />
        <AboutSection />
        <ViolationsShowcase />
        <CaseStudiesSection />
      </div>
    </div>
  )
}
