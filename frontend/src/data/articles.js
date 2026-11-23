export const featuredArticle = {
  slug: 'salmas-story',
  category: 'Student story',
  date: '20 Oct 2026',
  dateTime: '2026-10-20',
  readTime: '6 min read',
  title: 'From Ouarzazate to engineering school: Salma’s story',
  excerpt:
    'Salma joined her first AFS workshop at sixteen. Three years and two mentors later, she starts at an engineering school this autumn — and now mentors two students herself.',
  author: 'Yasmine El Idrissi',
  authorRole: 'Communication volunteer',
  authorImage: '/assets/images/blog/latest4.jpg',
  image: '/assets/images/blog/heroblog.jpg',
  imageAlt: 'Students smiling together at an AFS gathering',
  body: [
    {
      heading: 'A workshop she almost skipped',
      paragraphs: [
        'Salma grew up in Ouarzazate, far from the universities she read about online. When a teacher told her about an AFS coding workshop at her school, she signed up mostly to keep a friend company.',
        'By the end of the afternoon she had built her first web page, and asked one of the volunteers how she could learn more. That question led to her first mentor.',
      ],
      quote: '“I didn’t know you could just ask. Once I did, people kept opening doors for me.”',
      quoteAuthor: 'Salma, AFS student',
    },
    {
      heading: 'Two mentors, one plan',
      paragraphs: [
        'Her first mentor, a software engineer in Casablanca, helped her plan her last two years of high school: which subjects to focus on, which competitions to enter and how to prepare for entrance exams.',
      ],
      figure: {
        image: '/assets/images/gallery/Youth Summit 2026.png',
        alt: 'Young people gathered around workshop equipment',
        caption: 'Students at an AFS coding workshop during the Youth Summit 2026.',
      },
      continuation: 'A second mentor joined when it was time to apply. Together they worked on her motivation letters and practised interviews over video calls.',
    },
    {
      heading: 'Paying it forward',
      paragraphs: [
        'This autumn Salma starts at an engineering school. She also mentors two students from her old high school, meeting each of them once a month.',
        'Her advice to students who are where she was three years ago is simple: come to one event, and ask one question.',
      ],
    },
  ],
};

const articles = [
  {
    slug: 'what-600-students-taught-us',
    category: 'Events',
    date: '12 Oct 2026',
    dateTime: '2026-10-12',
    title: 'What 600 students taught us at the Youth Summit',
    excerpt:
      'Three days, twelve workshops and one clear message: young Moroccans are ready to lead.',
    image: '/assets/images/blog/latest1.jpg',
    imageAlt: 'AFS volunteers welcoming students at an outreach event',
  },
  {
    slug: 'back-from-the-atlas',
    category: 'Events',
    date: '18 Jun 2026',
    dateTime: '2026-06-18',
    title: 'Back from the Atlas: our biggest outreach day yet',
    excerpt:
      'Forty volunteers, two schools and 300 books delivered to Imlil in a single day.',
    image: '/assets/images/blog/latest2.jpg',
    imageAlt: 'AFS students and volunteers gathered in the Atlas Mountains',
  },
  {
    slug: 'three-new-partners',
    category: 'Partners',
    date: '2 Jun 2026',
    dateTime: '2026-06-02',
    title: 'Three new partners join the AFS network',
    excerpt:
      'Two tech companies and a university will offer internships and host workshops next year.',
    image: '/assets/images/blog/latest3.png',
    imageAlt: 'Students and volunteers outside a school building',
  },
  {
    slug: 'karim-on-finding-a-mentor',
    category: 'Student stories',
    date: '21 May 2026',
    dateTime: '2026-05-21',
    title: '“I didn’t know I could ask”: Karim on finding a mentor',
    excerpt:
      'How one conversation at a summit turned into a year of guidance and a first internship.',
    image: '/assets/images/blog/latest4.jpg',
    imageAlt: 'An AFS participant wearing a shirt about finding success',
  },
  {
    slug: 'volunteer-applications-2026-27',
    category: 'Announcements',
    date: '3 May 2026',
    dateTime: '2026-05-03',
    title: 'Volunteer applications are open for 2026–27',
    excerpt:
      'We’re looking for mentors, workshop leads and photographers in five cities.',
    image: '/assets/images/blog/latest5.jpg',
    imageAlt: 'Young students together at an AFS gathering',
  },
  {
    slug: 'scholarship-clinic-in-rabat',
    category: 'Events',
    date: '10 Apr 2026',
    dateTime: '2026-04-10',
    title: 'Recap: scholarship clinic in Rabat',
    excerpt:
      'Ninety students got one-to-one help with their applications in a single afternoon.',
    image: '/assets/images/blog/latest6.jpg',
    imageAlt: 'Volunteers and students at an AFS outreach day',
  },
];

export default articles;

const allArticles = [featuredArticle, ...articles];

export const articlePath = (article) => `/news/${article.slug}`;
export const getArticle = (slug) => allArticles.find((article) => article.slug === slug);
