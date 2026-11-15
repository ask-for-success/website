import React from 'react';
import events, { pastEvents } from '../data/events.js';
import { ArrowRight, MapPin } from 'lucide-react';

const registrationLink = (eventTitle) =>
  `mailto:askforsuccess@gmail.com?subject=${encodeURIComponent(`Registration for ${eventTitle}`)}`;

export default function Events() {
  return (
    <>
      <section className="events-hero" aria-labelledby="events-hero-title">
        <div className="container events-hero-layout">
          <div className="events-hero-content">
            <h1 id="events-hero-title">
              Events that
              <span>open doors</span>
            </h1>

            <p>
              Summits, workshops and outreach days where students meet mentors,
              partners and each other. Every event is free for students.
            </p>

            <a className="events-hero-button" href="#upcoming-events">
              See upcoming events
            </a>
          </div>

          <div className="events-hero-image">
            <img
              src="/assets/images/events/ae7e326ca36d4f5be0294fbfa83ac4ee706843af.jpg"
              alt="AFS students and volunteers gathered at an outreach event"
              fetchPriority="high"
            />
          </div>
        </div>
      </section>

      <section className="next-event-section" aria-labelledby="next-event-title">
        <div className="container">
          <header className="next-event-heading">
            <h2 id="next-event-title">Next event</h2>
            <p>Registration is open.</p>
          </header>

          <div className="next-event-grid">
            <article className="next-event-card">
              <div className="next-event-photo">
                <img
                  src="/assets/images/events/ae7e326ca36d4f5be0294fbfa83ac4ee706843af.jpg"
                  alt="AFS participants gathered outdoors at an event in Ain Chok"
                  loading="lazy"
                />
                <span className="next-event-location">
                  <MapPin size={13} aria-hidden="true" />
                  Casablanca, Ain Chok
                </span>
              </div>

              <div className="next-event-card-content">
                <time className="next-event-date" dateTime="2026-10-31">
                  31 OCT 2026
                </time>
                <h3>Next Morocco Youth Summit 2026</h3>
                <p>
                  Join over 600 student delegates, startup founders, and
                  mentors for two days of collaborative innovation, keynote
                  addresses, and national hackathon presentations.
                </p>
                <a
                  className="next-event-outline-button"
                  href={registrationLink('Next Morocco Youth Summit 2026')}
                >
                  Register now
                  <span aria-hidden="true"><ArrowRight size={13} /></span>
                </a>
              </div>
            </article>

            <aside className="next-event-panel" aria-label="Event details">
              <h3>Starts in</h3>
              <div
                className="next-event-countdown"
                aria-label="6 days, 14 hours, 32 minutes"
              >
                <div><strong>06</strong><span>days</span></div>
                <div><strong>14</strong><span>hours</span></div>
                <div><strong>32</strong><span>min</span></div>
              </div>

              <dl className="next-event-facts">
                <div><dt>Date</dt><dd>31 Oct 2026</dd></div>
                <div><dt>Time</dt><dd>9:00 – 18:00</dd></div>
                <div><dt>Venue</dt><dd>Ain Chok, Casablanca</dd></div>
                <div><dt>Seats left</dt><dd>112 of 600</dd></div>
                <div><dt>Price</dt><dd>Free for students</dd></div>
              </dl>

              <a
                className="next-event-register-button"
                href={registrationLink('Next Morocco Youth Summit 2026')}
              >
                Register now
              </a>
              <p className="next-event-deadline">
                Registration closes on 28 October.
              </p>
            </aside>
          </div>
        </div>
      </section>

      <section className="events-upcoming-section" id="upcoming-events">
        <div className="container">
          <header className="events-upcoming-heading">
            <h2>Upcoming events</h2>
            <p>Pick one and save your seat.</p>
          </header>

          <div className="events-upcoming-grid">
            {events.map((event) => (
              <article className="events-upcoming-card" key={event.id}>
                <time className="events-upcoming-date" dateTime={event.dateTime}>
                  {event.date}
                </time>
                <h3>{event.title}</h3>
                <p>{event.description}</p>
                <a
                  className="events-upcoming-register"
                  href={registrationLink(event.title)}
                  aria-label={`Register for ${event.title}`}
                >
                  Register now
                  <span aria-hidden="true"><ArrowRight size={13} /></span>
                </a>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="events-past-section" aria-labelledby="past-events-title">
        <div className="container">
          <header className="events-past-heading">
            <h2 id="past-events-title">Past events</h2>
            <p>What we’ve done together so far.</p>
          </header>

          <div className="events-past-grid">
            {pastEvents.map((event) => (
              <article className="events-past-card" key={event.id}>
                <div className="events-past-photo">
                  <img src={event.image} alt={event.imageAlt} loading="lazy" />
                </div>
                <div className="events-past-content">
                  <time className="events-past-date" dateTime={event.dateTime}>
                    {event.date}
                  </time>
                  <h3>{event.title}</h3>
                  <p className="events-past-location">
                    <MapPin size={14} aria-hidden="true" />
                    {event.location}
                  </p>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
