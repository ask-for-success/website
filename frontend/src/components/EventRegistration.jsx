import React, { useEffect, useState } from 'react';
import { eventEmail, todayInMorocco } from '../data/events.js';

const countdownUnits = [
  ['days', 1440, Infinity],
  ['hours', 60, 24],
  ['min', 1, 60],
];

const deadlineFormat = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric', month: 'long', timeZone: 'UTC',
});

export default function EventRegistration({ event }) {
  const [now, setNow] = useState(Date.now);
  const minutes = Math.ceil((Date.parse(event.start) - now) / 60_000);
  const hasStarted = minutes <= 0;
  const registrationOpen = !hasStarted && todayInMorocco(now) <= event.registrationCloses;
  const deadline = deadlineFormat.format(new Date(event.registrationCloses));
  const facts = [
    ['Date', event.displayDate], ['Time', event.hours], ['Venue', event.location],
    ['Seats left', 'Check by email'], ['Price', event.price],
  ];

  useEffect(() => {
    if (hasStarted) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [hasStarted]);

  return (
    <aside className="next-event-panel" aria-label="Event registration">
      <h3>{hasStarted ? 'Event date passed' : 'Starts in'}</h3>
      {!hasStarted ? (
        <div className="next-event-countdown">
          {countdownUnits.map(([label, unit, rollover]) => {
            const value = Math.floor(minutes / unit) % rollover;
            return <div key={label}><strong>{String(value).padStart(2, '0')}</strong><span>{label}</span></div>;
          })}
        </div>
      ) : (
        <p className="next-event-countdown next-event-countdown--past">
          This event was scheduled for {event.displayDate}.
        </p>
      )}

      <dl className="next-event-facts">
        {facts.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
      </dl>

      <a
        className="home-button home-button--large home-button--filled next-event-register-button"
        href={eventEmail(event, registrationOpen ? 'Registration for' : 'Question about')}
      >
        {registrationOpen ? 'Register now' : 'Ask about this event'}
      </a>
      <p className="next-event-deadline">
        Registration {registrationOpen ? 'closes' : 'closed'} on {deadline}.
      </p>
    </aside>
  );
}
