const summitDate = '2026-10-31';
const summitLocation = 'Ain Chok, Casablanca';

export const featuredEvent = {
  slug: 'morocco-youth-summit-2026',
  title: 'Next Morocco Youth Summit 2026',
  category: 'Summit',
  date: '31 OCT 2026',
  dateTime: summitDate,
  displayDate: '31 Oct 2026',
  start: `${summitDate}T09:00:00+01:00`,
  hours: '9:00 – 18:00',
  location: summitLocation,
  locationBadge: 'Casablanca, Ain Chok',
  locationNote: 'The exact address is sent by email after registration.',
  image: '/assets/images/events/ae7e326ca36d4f5be0294fbfa83ac4ee706843af.jpg',
  homeImage: '/assets/images/home/upcoming.jpg',
  imageAlt: 'AFS participants gathered outdoors at an event in Ain Chok',
  description: 'Join over 600 student delegates, startup founders, and mentors for two days of collaborative innovation, keynote addresses, and national hackathon presentations.',
  price: 'Free for students',
  registrationCloses: '2026-10-28',
  overview: [
    'The Morocco Youth Summit brings together more than 600 high-school and university students with startup founders, engineers and mentors who started where they are now.',
    'Students choose a workshop, meet partners over lunch and end the day with a national hackathon, where teams present their ideas to a jury. Participation is free for students and lunch is provided.',
  ],
  program: [
    ['09:00', 'Welcome and registration', 'Pick up your badge and meet the volunteers.'],
    ['10:00', 'Opening keynote', 'How young Moroccans are building careers in tech and beyond.'],
    ['11:00', 'Workshops', 'Choose one: coding, design, public speaking or scholarship applications.'],
    ['13:00', 'Lunch and networking', 'Meet mentors and partners over lunch.'],
    ['14:30', 'Hackathon presentations', 'Student teams pitch their projects to the jury.'],
    ['17:30', 'Awards and closing', 'Winners announced, followed by the group photo.'],
  ],
  speakers: [
    ['NB', 'Nadia Benali', 'Software engineer, mentor'],
    ['OH', 'Omar Haddad', 'Startup founder'],
    ['IC', 'Imane Chraibi', 'Scholarship advisor'],
    ['YA', 'Youssef Amrani', 'Design lead, partner company'],
  ],
};

const events = [
  {
    slug: 'coding-workshop-build-a-website',
    date: '31 OCT 2026',
    dateTime: '2026-10-31',
    title: 'Coding workshop: build a website',
    description:
      'A hands-on afternoon for high-school students. Bring a laptop; we provide everything else, including mentors from our partner companies.',
  },
  {
    slug: 'scholarship-application-clinic',
    date: '31 OCT 2026',
    dateTime: '2026-10-31',
    title: 'Scholarship application clinic',
    description:
      'One-to-one help with applications, motivation letters and interviews for students aiming to study abroad or in Morocco.',
  },
  {
    slug: 'rural-outreach-chefchaouen',
    date: '31 OCT 2026',
    dateTime: '2026-10-31',
    title: 'Rural outreach: Chefchaouen',
    description:
      'We bring books, laptops and a day of workshops to two schools in the province. Volunteers welcome.',
  },
  {
    slug: 'online-careers-in-tech-panel',
    date: '31 OCT 2026',
    dateTime: '2026-10-31',
    title: 'Online: careers in tech panel',
    description:
      'Five young Moroccan engineers share how they got their first job. Live Q&A in Darija, French and English.',
  },
];

export const pastEvents = [
  {
    slug: 'atlas-mountains-outreach-day',
    date: '14 JUN 2026',
    dateTime: '2026-06-14',
    image: '/assets/images/events/0ef239aa3dd39802f19cd75e0f8a89f0bf2b0250.jpg',
    imageAlt: 'AFS students holding flags in the Atlas Mountains',
    title: 'Atlas Mountains outreach day',
    location: 'Imlil, Al Haouz',
  },
  {
    slug: 'lycee-leadership-workshop',
    date: '22 MAR 2026',
    dateTime: '2026-03-22',
    image: '/assets/images/events/ff3bbda3f454f12cbf8b2d9de4d89ccfc54e7fa5.png',
    imageAlt: 'Students and volunteers gathered in a school courtyard',
    title: 'Lycée leadership workshop',
    location: 'Lycée Mohammed V, Casablanca',
  },
  {
    slug: 'youth-summit-2025',
    date: '7 DEC 2025',
    dateTime: '2025-12-07',
    image: '/assets/images/events/f2c3647cd542dcf4f487eb0de13ed06b93371eaf.jpg',
    imageAlt: 'Students taking part in a youth summit',
    title: 'Youth Summit 2025',
    location: 'Ain Chok, Casablanca',
  },
];

export default events;

const allEvents = [featuredEvent, ...events, ...pastEvents];
const eventDateFormat = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Africa/Casablanca' });

export const eventPath = (event) => `/events/${event.slug}`;
export const getEvent = (slug) => allEvents.find((event) => event.slug === slug);
export const todayInMorocco = (now = Date.now()) => eventDateFormat.format(now);
export const eventEmail = (event, subject) =>
  `mailto:askforsuccess@gmail.com?subject=${encodeURIComponent(`${subject} ${event.title}`)}`;
