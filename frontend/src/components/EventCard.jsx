import React from 'react';
import { Link } from 'react-router-dom';

export default function EventCard({ event }) {
  return (
    <article className="content-card event-card">
      <div className="event-date">
        <span>{event.month}</span>
        <strong>{event.day}</strong>
      </div>
      <div>
        <p className="card-kicker">{event.type}</p>
        <h3>{event.title}</h3>
        <p className="card-copy">{event.location}</p>
        <Link className="text-link" to="/events">Event details <span aria-hidden="true">→</span></Link>
      </div>
    </article>
  );
}
