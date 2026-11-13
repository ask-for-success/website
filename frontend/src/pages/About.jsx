import React from 'react';
import { Link } from 'react-router-dom';
import StatsSection from '../components/StatsSection.jsx';
import {
  GraduationCap,
  Star,
  UsersRound,
  ChartNoAxesColumnIncreasing,
  ArrowRight,
  HeartHandshake,
  HandHeart,
  Handshake,
} from 'lucide-react';

export default function About() {
  return (
    <>
      {/* ABOUT PAGE - HERO SECTION */}
      <section className="about-hero">
        <div className="container about-hero-layout">
          {/* LEFT SIDE - TEXT */}
          <div className="about-hero-content">
            <h1>
              Opening doors for <br />
              the <span>next</span> <br />
              <span>generation.</span>
            </h1>

            <p className="about-hero-description">
              Ask For Success (AFS) is a Moroccan non-profit association
              dedicated to helping students and young people access the
              opportunities, education, and community support they need to
              succeed.{' '}
              <span>
                We believe every success story starts with someone willing to
                ask and someone ready to answer.
              </span>
            </p>
          </div>

          {/* RIGHT SIDE - IMAGE */}
          <div className="about-hero-visual">
            <img
              src="/assets/images/about/abou1.png"
              alt="Ask For Success association members"
              className="about-hero-image"
            />
          </div>
        </div>
      </section>

      {/* =====================================
    OUR MISSION SECTION
===================================== */}

      <section className="about-mission">
        {/* DECORATIVE CIRCLES */}
        <div className="mission-decoration mission-decoration-left">
          {Array.from({ length: 7 }, (_, i) => (
            <span key={i}></span>
          ))}
        </div>

        <div className="mission-decoration mission-decoration-right">
          {Array.from({ length: 7 }, (_, i) => (
            <span key={i}></span>
          ))}
        </div>

        <div className="container about-mission-content">
          <h2>Our Mission</h2>

          <p className="about-mission-subtitle">
            Turning potential into achievement, together.
          </p>

          <p className="about-mission-description">
            Our mission is to bridge the gap between ambition and opportunity.
            We work alongside students, volunteers, and partners to create real
            pathways — through events, mentorship, and community initiatives —
            that turn potential into achievement. AFS exists so that no young
            person's success depends only on where they started.
          </p>
        </div>
      </section>

      {/* =====================================
    WHAT DRIVES US FORWARD
===================================== */}

      <section className="about-values">
        <div className="container">
          {/* SECTION HEADER */}
          <div className="about-values-header">
            <div>
              <h2>What drives us forward</h2>
              <p>Four pillars, one purpose.</p>
            </div>

            <Link to="/get-involved" className="about-values-link">
              See how you can help
              <ArrowRight size={18} />
            </Link>
          </div>

          {/* VALUES GRID */}
          <div className="about-values-grid">
            {/* EDUCATION */}
            <article className="about-value-card">
              <div className="about-value-icon">
                <GraduationCap size={23} />
              </div>

              <h3>Education</h3>

              <p>
                We support learning beyond the classroom, through mentorship,
                workshops, and knowledge-sharing initiatives.
              </p>
            </article>

            {/* OPPORTUNITY */}
            <article className="about-value-card">
              <div className="about-value-icon">
                <Star size={23} />
              </div>

              <h3>Opportunity</h3>

              <p>
                We connect students with events, resources, and experiences that
                open doors they might not otherwise have access to.
              </p>
            </article>

            {/* COMMUNITY */}
            <article className="about-value-card">
              <div className="about-value-icon">
                <UsersRound size={23} />
              </div>

              <h3>Community</h3>

              <p>
                We build a network of students, volunteers, and partners who
                support each other and grow together.
              </p>
            </article>

            {/* IMPACT */}
            <article className="about-value-card">
              <div className="about-value-icon">
                <ChartNoAxesColumnIncreasing size={23} />
              </div>

              <h3>Impact</h3>

              <p>
                We measure success not just in numbers, but in the real change
                we help create in young people's lives.
              </p>
            </article>
          </div>
        </div>
      </section>
      <StatsSection />

      {/* =====================================
    WHERE IT ALL BEGAN
===================================== */}

      <section className="about-story">
        <div className="container about-story-layout">
          {/* LEFT - IMAGE */}
          <div className="about-story-image">
            <img
              src="/assets/images/about/about2.jpg"
              alt="Ask For Success volunteers and students"
              loading="lazy"
            />
          </div>

          {/* RIGHT - CONTENT */}
          <div className="about-story-content">
            <h2>Where it all began</h2>

            <p className="about-story-subtitle">
              A small idea that grew into a movement.
            </p>

            <p className="about-story-description">
              <span>Ask For Success</span> was founded with a simple belief:
              that success shouldn't be a privilege reserved for the few. What
              started as a small group of students and volunteers has grown into
              a community-driven association working across Morocco to support
              the next generation.
            </p>
          </div>
        </div>
      </section>

      {/* =====================================
    BE PART OF THE STORY
===================================== */}

      <section className="about-join">
        <div className="container about-join-layout">
          {/* LEFT - CONTENT */}
          <div className="about-join-content">
            <h2>Be part of the story</h2>

            <p>
              Whether you volunteer your time, support a cause, or partner with
              us — you help write the next success story.
            </p>

            <div className="about-join-actions">
              <Link to="/get-involved" className="about-join-donate">
                Donate
              </Link>

              <Link to="/get-involved" className="about-join-partner">
                Become a partner
                <span className="about-join-arrow">
                  <ArrowRight size={15} />
                </span>
              </Link>
            </div>
          </div>

          {/* RIGHT - THREE WAYS TO HELP */}
          <div className="about-help-card">
            <h3>Three ways to help</h3>

            <div className="about-help-item">
              <span className="about-help-icon">
                <HandHeart size={20} />
              </span>

              <div>
                <h4>Volunteer</h4>
                <p>Give your time, energy, workshops, and mentoring.</p>
              </div>
            </div>

            <div className="about-help-item">
              <span className="about-help-icon">
                <Handshake size={20} />
              </span>

              <div>
                <h4>Partner</h4>
                <p>Collaborate with us to open more doors for students.</p>
              </div>
            </div>

            <div className="about-help-item">
              <span className="about-help-icon">
                <HeartHandshake size={20} />
              </span>

              <div>
                <h4>Donate</h4>
                <p>Fund learning programs and community initiatives.</p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
