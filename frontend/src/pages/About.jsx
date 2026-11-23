import React from 'react';
import { Link } from 'react-router-dom';
import StatsSection from '../components/StatsSection.jsx';

const icons = '/assets/icons/about';

export default function About() {
  return (
    <>
      {/* ABOUT PAGE - HERO SECTION */}
      <section className="about-hero">
        <div className="about-hero-layout">
          {/* LEFT SIDE - TEXT */}
          <div className="about-hero-content">
            <h1>
              Opening doors for the <span>next generation.</span>
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
              fetchPriority="high"
            />
          </div>
        </div>
      </section>
      <section className="about-mission">
        <img className="mission-decoration mission-decoration-left" src="/assets/images/about/mission-rings-left.png" alt="" />
        <img className="mission-decoration mission-decoration-right" src="/assets/images/about/mission-rings-right.png" alt="" />
        <div className="site-shell about-mission-content">
          <div className="about-mission-heading">
            <h2>Our Mission</h2>
            <p>Turning potential into achievement, together.</p>
          </div>

          <p className="about-mission-description">
            Our mission is to bridge the gap between ambition and opportunity.
            We work alongside students, volunteers, and partners to create real
            pathways — through events, mentorship, and community initiatives —
            that turn potential into achievement. AFS exists so that no young
            person's success depends only on where they started.
          </p>
        </div>
      </section>
      <section className="about-values">
        <div className="site-shell">
          {/* SECTION HEADER */}
          <div className="about-values-header">
            <div>
              <h2>What drives us forward</h2>
              <p>Four pillars, one purpose.</p>
            </div>

            <Link to="/get-involved" className="home-button home-button--large about-values-link">
              See how you can help
              <img src="/assets/icons/home/arrow-view-all.svg" alt="" />
            </Link>
          </div>

          {/* VALUES GRID */}
          <div className="about-values-grid">
            {/* EDUCATION */}
            <article className="about-value-card">
              <div className="about-value-icon">
                <img src={`${icons}/education.svg`} alt="" />
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
                <img src={`${icons}/opportunity.svg`} alt="" />
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
                <img src={`${icons}/community.svg`} alt="" />
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
                <img src={`${icons}/impact.svg`} alt="" />
              </div>

              <h3>Impact</h3>

              <p>
                We measure success not just in numbers, but in the real change
                we help create in young people’s lives.
              </p>
            </article>
          </div>
        </div>
      </section>
      <StatsSection />
      <section className="about-story">
        <div className="site-shell about-story-layout">
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
      <section className="about-join">
        <div className="site-shell about-join-layout">
          {/* LEFT - CONTENT */}
          <div className="about-join-content">
            <h2>Be part of the story</h2>

            <p>
              Whether you volunteer your time, support a cause, or partner with
              us, you help write the next success story.
            </p>

            <div className="about-join-actions">
              <Link to="/get-involved#donate" className="home-button home-button--large home-button--filled">
                Donate
              </Link>

              <Link to="/get-involved#partner" className="home-button home-button--large home-button--outline">
                Become a partner
                <img src="/assets/icons/home/arrow-outlined.svg" alt="" />
              </Link>
            </div>
          </div>

          {/* RIGHT - THREE WAYS TO HELP */}
          <div className="about-help-card">
            <h3>Three ways to help</h3>

            <div className="about-help-item">
              <span className="about-help-icon">
                <img src={`${icons}/volunteer.svg`} alt="" />
              </span>

              <div>
                <h4>Volunteer</h4>
                <p>Give your time at events, workshops, and mentoring.</p>
              </div>
            </div>

            <div className="about-help-item">
              <span className="about-help-icon">
                <img src={`${icons}/partner.svg`} alt="" />
              </span>

              <div>
                <h4>Partner</h4>
                <p>Collaborate with us to open more doors for students.</p>
              </div>
            </div>

            <div className="about-help-item">
              <span className="about-help-icon">
                <img src={`${icons}/donate.svg`} alt="" />
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
