import React from 'react';
import { Link } from 'react-router-dom';
import { eventPath } from '../data/events.js';

export function EventDetailsLink({ event }) {
  return (
    <Link
      className="home-button home-button--outline events-details-button"
      to={eventPath(event)}
      aria-label={`View details for ${event.title}`}
    >
      View details
      <img src="/assets/icons/home/event-arrow.svg" alt="" />
    </Link>
  );
}

export default function UpcomingEventCard({ event }) {
  return (
    <article className="events-upcoming-card">
      <time className="events-upcoming-date" dateTime={event.dateTime}>{event.date}</time>
      <h3>{event.title}</h3>
      <p>{event.description}</p>
      <EventDetailsLink event={event} />
    </article>
  );
}
