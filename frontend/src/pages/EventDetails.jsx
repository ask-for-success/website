import React from 'react';
import { useParams } from 'react-router-dom';
import { DetailBackLink, DetailMeta, DetailNotFound } from '../components/DetailNavigation.jsx';
import EventRegistration from '../components/EventRegistration.jsx';
import UpcomingEventCard from '../components/UpcomingEventCard.jsx';
import events, { eventEmail, getEvent, pastEvents, todayInMorocco } from '../data/events.js';

function EventProgram({ program }) {
  return (
    <section className="detail-section">
      <h2>Program</h2>
      <ol className="event-detail-program">
        {program.map(([time, title, description]) => (
          <li key={time}>
            <time dateTime={time}>{time}</time>
            <div>
              <h3>{title}</h3>
              <p>{description}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

function EventSpeakers({ speakers }) {
  return (
    <section className="detail-section">
      <h2>Speakers &amp; mentors</h2>
      <ul className="event-detail-speakers">
        {speakers.map(([initials, name, role]) => (
          <li key={name}>
            <span className="event-detail-avatar" aria-hidden="true">{initials}</span>
            <div>
              <h3>{name}</h3>
              <p>{role}</p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function EventLocation({ event }) {
  const mapUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(event.location)}`;

  return (
    <section className="detail-section">
      <h2>Location</h2>
      <div className="event-detail-location">
        <div className="event-detail-address">
          <span className="event-detail-avatar" aria-hidden="true">
            <img src="/assets/icons/details/location-chip.svg" alt="" width="24" height="24" />
          </span>
          <div>
            <h3>{event.location}</h3>
            <p>{event.locationNote}</p>
          </div>
        </div>
        <div className="event-detail-map" aria-hidden="true">
          <img src="/assets/icons/details/map.svg" alt="" width="48" height="48" />
        </div>
        <a className="detail-back-link" href={mapUrl}>
          Open in Google Maps
          <img src="/assets/icons/home/arrow-text.svg" alt="" width="20" height="20" />
        </a>
      </div>
    </section>
  );
}

export default function EventDetails() {
  const { slug } = useParams();
  const event = getEvent(slug);
  if (!event) {
    return <DetailNotFound title="Event not found" description="This event could not be found. Browse the Events page for available listings." backTo="/events" backLabel="Back to events" />;
  }

  const today = todayInMorocco();
  const isArchived = pastEvents.includes(event);
  const eventDatePassed = event.dateTime < today;
  const relatedEvents = events.filter((related) => related.slug !== event.slug);

  return (
    <div className="site-shell detail-page event-detail">
      <header className="detail-header">
        <DetailBackLink to="/events">Back to events</DetailBackLink>
        <div className="detail-title">
          {event.category && <span className="listing-chip">{event.category}</span>}
          <h1>{event.title}</h1>
          <div className="detail-meta">
            <DetailMeta icon="calendar"><time dateTime={event.dateTime}>{event.displayDate ?? event.date}</time></DetailMeta>
            {event.hours && <DetailMeta icon="clock">{event.hours}</DetailMeta>}
            {event.location && <DetailMeta icon="location">{event.location}</DetailMeta>}
          </div>
        </div>
        {event.image && <img className="detail-cover event-detail-cover" src={event.image} alt={event.imageAlt} fetchPriority="high" />}
      </header>

      <div className={event.registrationCloses ? 'event-detail-body event-detail-body--summit' : 'event-detail-body'}>
        <div className="event-detail-main">
          {event.description && (
            <section className="detail-section detail-prose">
              <h2>About this event</h2>
              {(event.overview ?? [event.description]).map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
            </section>
          )}
          {event.program && <EventProgram program={event.program} />}
          {event.speakers && <EventSpeakers speakers={event.speakers} />}
          {event.locationNote && <EventLocation event={event} />}
          {isArchived && <p className="detail-content-note">The original listing provides the event date, location and photo. Further details are unavailable.</p>}
          {!isArchived && !event.registrationCloses && (
            <div className="detail-section">
              <p className="detail-content-note">The listing provides an overview and date. Further details are unavailable.</p>
              <a
                className="home-button home-button--large home-button--filled"
                href={eventEmail(event, eventDatePassed ? 'Question about' : 'Registration for')}
              >
                {eventDatePassed ? 'Ask about this event' : 'Register by email'}
              </a>
            </div>
          )}
        </div>
        {event.registrationCloses && <EventRegistration event={event} />}
      </div>

      <section className="detail-related" aria-labelledby="more-events-title">
        <header className="listing-section-title">
          <h2 id="more-events-title">More events</h2>
          <p>{relatedEvents.some((related) => related.dateTime >= today) ? 'Explore more events from AFS.' : 'Browse earlier workshops and outreach events.'}</p>
        </header>
        <div className="events-upcoming-grid">
          {relatedEvents.map((related) => <UpcomingEventCard key={related.slug} event={related} />)}
        </div>
      </section>
    </div>
  );
}
