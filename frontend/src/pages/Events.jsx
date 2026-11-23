import React from 'react';
import EventRegistration from '../components/EventRegistration.jsx';
import UpcomingEventCard, { EventDetailsLink } from '../components/UpcomingEventCard.jsx';
import events, { featuredEvent, pastEvents, todayInMorocco } from '../data/events.js';

export default function Events() {
  const today = todayInMorocco();
  const hasUpcomingEvents = events.some((event) => event.dateTime >= today);
  return (
    <>
      <section className="events-hero" aria-labelledby="events-hero-title">
        <div className="site-shell events-hero-layout">
          <div className="events-hero-content listing-intro">
            <h1 id="events-hero-title">
              Events that <span>open doors</span>
            </h1>

            <p>
              Summits, workshops and outreach days where students meet mentors,
              partners and each other. Every event is free for students.
            </p>

            <a className="home-button home-button--large home-button--filled" href="#upcoming-events">
              {hasUpcomingEvents ? 'See upcoming events' : 'See more events'}
            </a>
          </div>

          <div className="events-hero-image">
            <img
              src="/assets/images/gallery/Youth Summit 2026.png"
              alt="Students gathered around workshop equipment"
              fetchPriority="high"
            />
          </div>
        </div>
      </section>

      <section className="next-event-section" aria-labelledby="next-event-title">
        <div className="site-shell">
          <header className="listing-section-title events-section-title">
            <h2 id="next-event-title">{featuredEvent.dateTime >= today ? 'Next event' : 'Featured event'}</h2>
            <p>{today <= featuredEvent.registrationCloses ? 'Registration is open.' : 'Registration has closed.'}</p>
          </header>

          <div className="next-event-grid">
            <article className="next-event-card">
              <div className="next-event-photo">
                <img
                  src={featuredEvent.image}
                  alt={featuredEvent.imageAlt}
                  loading="lazy"
                />
                <span className="next-event-location">
                  <img src="/assets/icons/home/event-location.svg" alt="" />
                  {featuredEvent.locationBadge}
                </span>
              </div>

              <div className="next-event-card-content">
                <time className="next-event-date" dateTime={featuredEvent.dateTime}>
                  {featuredEvent.date}
                </time>
                <h3>{featuredEvent.title}</h3>
                <p>{featuredEvent.description}</p>
                <EventDetailsLink event={featuredEvent} />
              </div>
            </article>

            <EventRegistration event={featuredEvent} />
          </div>
        </div>
      </section>

      <section className="events-upcoming-section" id="upcoming-events" tabIndex={-1} aria-labelledby="upcoming-events-title">
        <div className="site-shell">
          <header className="listing-section-title events-section-title">
            <h2 id="upcoming-events-title">{hasUpcomingEvents ? 'Upcoming events' : 'More events'}</h2>
            <p>{hasUpcomingEvents ? 'Explore the schedule.' : 'Browse earlier workshops and outreach events.'}</p>
          </header>

          <div className="events-upcoming-grid">
            {events.map((event) => <UpcomingEventCard key={event.slug} event={event} />)}
          </div>
        </div>
      </section>

      <section className="events-past-section" aria-labelledby="past-events-title">
        <div className="site-shell">
          <header className="listing-section-title events-section-title">
            <h2 id="past-events-title">Past events</h2>
            <p>What we’ve done together so far.</p>
          </header>

          <div className="events-past-grid">
            {pastEvents.map((event) => (
              <article className="events-past-card" key={event.slug}>
                <div className="events-past-photo">
                  <img src={event.image} alt={event.imageAlt} loading="lazy" />
                </div>
                <div className="events-past-content">
                  <time className="events-past-date" dateTime={event.dateTime}>
                    {event.date}
                  </time>
                  <h3>{event.title}</h3>
                  <p className="events-past-location">
                    <img src="/assets/icons/events/past-location.svg" alt="" />
                    {event.location}
                  </p>
                  <EventDetailsLink event={event} />
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
