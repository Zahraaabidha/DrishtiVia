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
    <div className="w-full" style={{ position: 'relative', backgroundColor: '#0a0a0a' }}>
      <div style={{ position: 'relative', zIndex: 10 }}>
        <HeroSection />
        <PinnedTextReveal />
        <AboutSection />
        <ViolationsShowcase />
        <div style={{ marginBottom: '60vh' }}>
          <CaseStudiesSection />
        </div>
      </div>
      <Footer />
    </div>
  )
}
