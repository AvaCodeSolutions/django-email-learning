Introduction
============

Django Email Learning is an open-source Django application by `AvaCode Solutions`_  designed to help educators,
mentors, and developers create and manage automated learning paths.

.. _AvaCode Solutions: https://avacodesolutions.com/
.. _GitHub: https://github.com/AvaCodeSolutions/django-email-learning

Unlike traditional Learning Management Systems (LMS) that require students
to log into a complex dashboard to find their content, Django Email Learning delivers
lessons directly to the learner's inbox, ensuring high engagement where users
already spend their time.

If you find this project useful, a star on `GitHub`_ helps others discover it.

Want to try it online first? Create a free account on `InboxAcademy <https://inboxacademy.io>`_, our hosted platform built on top of Django Email Learning.


Key Features
------------

* **Course Orchestration:** Easily define a sequence of lessons, quizzes, and assignments.
* **Email-First Delivery:** Lessons are delivered via automated email triggers based on learner progress.
* **Enrollment Pages:** Built-in public pages for learner registration.
* **Progress Tracking:** Real-time analytics on lesson sent, quiz completions, and learner bottlenecks.
* **Django Native:** Built as a pluggable Django app that integrates seamlessly into your existing project.

Try It as a Learner
-------------------

To experience Django Email Learning from a learner perspective, enroll in a public course at:

`InboxAcademy <https://inboxacademy.io/learning/public/organizations/1/>`_

How It Works
------------

The platform follows a simple three-step lifecycle:

1. **Design:** You define your Organizations, Courses, Lessons, and Quizzes in the platform section.
2. **Enroll:** Learners join via a public-facing enrollment page. They need to provide their email to start.
3. **Automate:** A background worker (Cron Job) monitors the schedule and sends the next piece of content to the learner's email.

Who Is This For?
----------------

* **Developers:** Looking to add "drip-feed" educational content to an existing Django site.
* **Content Creators:** Who want a lightweight, "distraction-free" way to teach their audience.
* **Bootcamps & Organizations:** Needing a way to automate onboarding or training without forcing users to learn a new UI.

The Philosophy
--------------

Most Learning Management Systems (LMS) suffer from **"Dashboard Fatigue"**—learners sign up with high intent but rarely log back in. Furthermore, traditional web-based platforms often exclude learners in regions with unstable internet connections or limited data access.

**Django Email Learning** was built to solve these challenges by meeting learners where they already are: their **inbox**.


By shifting the delivery from a heavy web interface to lightweight, automated email triggers, we provide:

* **Offline Access:** Once an email is received, the lesson content is available to the learner regardless of their current connectivity.
* **Reduced Friction:** No need to remember passwords or navigate a complex UI; the content comes to the user.
* **Consistency:** By combining Django’s robust database logic with automated scheduling, we transform learning from a "destination" they have to visit into a passive, consistent habit.

Next Steps
----------

* To get started with a new installation, head over to the :doc:`installation` guide.
