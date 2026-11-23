import React from 'react';
import { Link } from 'react-router-dom';
import StatsSection from '../components/StatsSection.jsx';
import { eventPath, featuredEvent, todayInMorocco } from '../data/events.js';

const icons = '/assets/icons/home';

function HomeEventCard({ featured = false }) {
  const event = featuredEvent;
  return (
    <article className={featured ? 'home-event-card home-event-featured' : 'home-event-card home-event-small'}>
      {featured && (
        <div className="home-event-image">
          <img
            src={event.homeImage}
            alt={event.imageAlt}
            loading="lazy"
          />
          <span className="home-event-location">
            <img src={`${icons}/event-location.svg`} alt="" />
            {event.locationBadge}
          </span>
        </div>
      )}

      <div className="home-event-content">
        <time className="home-event-date" dateTime={event.dateTime}>
          {event.date}
        </time>
        <h3>{event.title}</h3>
        <p>{event.description}</p>
        <Link to={eventPath(event)} className="home-button home-button--outline home-event-button" aria-label={`View details for ${event.title}`}>
          View details
          <img src={`${icons}/event-arrow.svg`} alt="" />
        </Link>
      </div>
    </article>
  );
}

export default function Home() {
  return (
    <>
      <section className="hero">
        <div className="site-shell hero-layout">
          <div className="hero-text">
            <h1>
              Where your success story <span>begins</span>
            </h1>

            <p className="hero-description">
              Empowering Morocco’s youth through mentorship, education,
              leadership, and community.
            </p>

            <div className="hero-actions">
              <Link to="/get-involved#donate" className="home-button home-button--large home-button--filled">
                Donate
              </Link>

              <Link to="/get-involved#partner" className="home-button home-button--large home-button--outline">
                Become a partner
                <img src={`${icons}/arrow-outlined.svg`} alt="" />
              </Link>
            </div>
          </div>

          <div className="hero-visual">
            <img
              src="/assets/images/home/hero.jpg"
              alt="Young students participating in an AFS community initiative"
              className="hero-photo"
              fetchPriority="high"
            />
          </div>
        </div>
      </section>

      {/* ABOUT OUR ASSOCIATION */}
      <section className="home-about">
        <div className="site-shell home-about-layout">
          {/* LEFT: IMAGE */}
          <div className="home-about-image">
            <img
              src="/assets/images/home/home about.jpg"
              alt="AFS volunteer representing the association"
              loading="lazy"
            />
          </div>

          {/* RIGHT: CONTENT */}
          <div className="home-about-content">
            <div className="home-about-copy">
              <h2>About Our Association</h2>

              <div className="home-about-description">
                <p>
                  <strong>Ask For Success</strong> is a Moroccan non-profit
                  dedicated to opening doors for students and young people.
                </p>
                <p>
                  Through events, mentorship, and community support, we help
                  turn opportunity into real success stories.
                </p>
              </div>
            </div>

            {/* FEATURE BADGES */}
            <div className="home-about-features">
              <div className="home-about-feature">
                <img src={`${icons}/education.svg`} alt="" />
                <span>Education &amp; mentorship</span>
              </div>

              <div className="home-about-feature">
                <img src={`${icons}/opportunity.svg`} alt="" />
                <span>Opportunity access</span>
              </div>

              <div className="home-about-feature">
                <img src={`${icons}/community.svg`} alt="" />
                <span>Community events</span>
              </div>

              <div className="home-about-feature">
                <img src={`${icons}/impact.svg`} alt="" />
                <span>Measurable impact</span>
              </div>
            </div>

            {/* BUTTON */}
            <Link to="/about" className="home-button home-button--large home-button--outline">
              Learn More About Us
              <img src={`${icons}/arrow-outlined.svg`} alt="" />
            </Link>
          </div>
        </div>
      </section>

      <StatsSection />

      {/* WAYS TO GET INVOLVED */}
      <section className="home-involved">
        <div className="site-shell">
          {/* SECTION HEADER */}
          <div className="home-involved-header">
            <div>
              <h2>Ways to get involved</h2>
              <p className="home-involved-subtitle">
                Three ways to make an impact.
              </p>
            </div>

            <p className="home-involved-intro">
              Every contribution—whether your time, professional expertise, or
              financial patronage—directly enriches a young Moroccan's future.
            </p>
          </div>

          {/* THREE CARDS */}
          <div className="home-involved-grid">
            {/* DONATE */}
            <article className="home-involved-card">
              <div className="home-involved-icon">
                <img src={`${icons}/donate.svg`} alt="" />
              </div>

              <h3>Donate</h3>
              <p>
                Fuel student workshops, hardware tech kits, and rural youth
                outreach programs with tax-deductible contributions.
              </p>

              <Link to="/get-involved#donate" className="home-button home-involved-link" aria-label="Learn more about donating">
                Learn more
                <img src={`${icons}/arrow-text.svg`} alt="" />
              </Link>
            </article>

            {/* VOLUNTEER */}
            <article className="home-involved-card">
              <div className="home-involved-icon">
                <img src={`${icons}/volunteer.svg`} alt="" />
              </div>

              <h3>Volunteer</h3>
              <p>
                Offer your mentorship or operational time to empower Moroccan
                students across regional chapters and workshops.
              </p>

              <Link to="/get-involved#volunteer" className="home-button home-involved-link" aria-label="Learn more about volunteering">
                Learn more
                <img src={`${icons}/arrow-text.svg`} alt="" />
              </Link>
            </article>

            {/* PARTNER */}
            <article className="home-involved-card">
              <div className="home-involved-icon">
                <img src={`${icons}/partner.svg`} alt="" />
              </div>

              <h3>Partner</h3>
              <p>
                Collaborate as an educational institution, international NGO, or
                corporate sponsor for long-term career ecosystems.
              </p>

              <Link to="/get-involved#partner" className="home-button home-involved-link" aria-label="Learn more about partnering">
                Learn more
                <img src={`${icons}/arrow-text.svg`} alt="" />
              </Link>
            </article>
          </div>
        </div>
      </section>

      {/* UPCOMING EVENTS */}
      <section className="home-events">
        <div className="site-shell">
          <div className="home-events-header">
            <div>
              <h2>{featuredEvent.dateTime >= todayInMorocco() ? 'Upcoming Events' : 'Featured Events'}</h2>
              <p>Three ways to make an impact.</p>
            </div>

            <Link to="/events" className="home-button home-button--large home-events-view-all">
              View All events
              <img src={`${icons}/arrow-view-all.svg`} alt="" />
            </Link>
          </div>

          <div className="home-events-grid">
            <HomeEventCard featured />

            <div className="home-events-side">
              <HomeEventCard />
              <HomeEventCard />
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
