Branching Courses
=================

By default a course is one sequence: every learner receives the same content in the same order.
Branching lets a course send learners down different paths instead — onto a remedial track when
they fail a quiz, onto an advanced track when they score well, or onto whichever track they choose
by answering a question.

The course is still a sequence. Branching adds three things to it:

**Tracks**
  Named runs of content that sit beside the main path. A learner only receives a track's content
  when a routing rule sends them there.

**Routing rules**
  Rules on a quiz or a decision point that say which track a learner goes to, based on their
  quiz result or the answer they picked. Content with routing rules is called a *branch point*.

**Decision points**
  A content type that asks learners one question with two or more answers and no right answer.
  The answer they pick is what the routing rules match.

Organization admins and editors can create and edit tracks and routing rules. Other roles can see
them, but not change them.

.. SCREENSHOT PLACEHOLDER
   File: docs/images/branching-flow-view.png
   Show: the Flow view of a course with a quiz routing onto a remedial track and a decision
   point routing onto another track, so the tinted track boxes and labelled arrows are visible.

Tracks
------

Content that is not on a track is on the **main path**, and reaches every learner who is not
routed away from it. A track is a separate path through the course: learners reach it through a
routing rule, and once they have received its last content they continue where the track rejoins
the course.

Creating a Track
~~~~~~~~~~~~~~~~

On the course content page, click **Add Track** and fill in:

**Track name** (Required)
  How the track appears in the content table, the Flow view, and the track analytics.

**Branches off**
  **Main path**, or another track. A track that branches off another track is *nested* inside it:
  a learner who reaches it from its parent track is still on the parent track. Tracks can be nested
  up to ten levels deep.

**Rejoins the course at**
  The content where learners continue once they have finished the track, or **Ends the course**.
  The choices are limited to content on the main path and on the tracks this track branches off —
  a track can only rejoin somewhere outward from where it sits. A nested track that ends without a
  rejoin point continues wherever its parent track rejoins.

.. SCREENSHOT PLACEHOLDER
   File: docs/images/add-track-form.png
   Show: the Add Track form with a track name, "Branches off" set to Main path, and a rejoin
   point selected.

A track has to rejoin the course *after* the content that routes onto it. Rejoining at or before
that content would send learners onto the same track again, so a routing rule, a move, a reorder
or a track edit that would create that shape is refused with an explanation, and nothing is saved.

Adding Content to a Track
~~~~~~~~~~~~~~~~~~~~~~~~~

The lesson, quiz, assignment and decision forms have a **Track** field once the course has at least
one track. New content is added at the end of the chosen track; leave the field on **Main path**
for content every learner should receive.

To move existing content, change its **Track** in the form, or use **Move to** on its row in the
content table. Moved content goes to the end of its new track.

Content is ordered within its own track: drag rows to reorder a track, one track at a time.

Editing and Deleting a Track
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each track's header in the content table has an **Edit Track** and a **Delete Track** button. In the
Flow view, clicking a track's name opens it for editing too. Editing a track lets you rename it, and
change what it branches off or where it rejoins.

A track can only be deleted once it is empty — move or delete its content first. Deleting asks for
confirmation, and also removes the routing rules that send learners onto the track.

How Tracks Appear in the Content Table
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each track is listed directly under the content that routes onto it, indented:

- The track opens with a header naming the rule that selects it, such as **If failed** or
  **If score ≥ 80**.
- It closes with a row saying where learners continue: **Rejoins at** the rejoin content, or
  **Ends the course**.
- A track reached from more than one branch point appears once, under the first, noting the others
  with **Also reached from**.
- Tracks no routing rule reaches yet are listed at the bottom under **Tracks no rule routes onto
  yet**, so you can still edit them while you set up the rules.

.. SCREENSHOT PLACEHOLDER
   File: docs/images/content-table-tracks.png
   Show: the content table of a branching course, with a track header ("If failed"), the
   indented track content, and the "Rejoins at" row.

Routing Rules
-------------

Routing rules are added on a quiz or a decision point. Save the content first, then open it and go
to its **Branching** tab (the tab lists the course's tracks, so create at least one track first).

Each rule has a **When** condition and a **Send to** track. Use **Add rule** to add one, the arrows
to change their order, and **Save rules** to save the whole set at once.

.. SCREENSHOT PLACEHOLDER
   File: docs/images/quiz-branching-tab.png
   Show: the Branching tab of a quiz with two rules, e.g. "Failed → Remedial" and
   "Score at least 90 → Advanced".

How Rules Are Checked
~~~~~~~~~~~~~~~~~~~~~

Rules are checked from top to bottom, and **the first rule that matches decides** where the learner
goes. If no rule matches, the learner continues on their current path, exactly as if the content
had no rules.

**Otherwise** matches every result, so any rule after it could never match. An **Otherwise** rule
must therefore be the last rule; saving a set with **Otherwise** anywhere else is refused.

Conditions
~~~~~~~~~~

On a quiz:

========================  =========================================================
Condition                 Matches when
========================  =========================================================
**Passed**                The learner reached the quiz's passing score.
**Failed**                The learner did not reach the passing score.
**Score at least** *N*    The learner's score is *N* or higher (0–100).
**Score below** *N*       The learner's score is lower than *N*.
**Otherwise**             Any result.
========================  =========================================================

On a decision point:

========================  =========================================================
Condition                 Matches when
========================  =========================================================
**Answered** *answer*     The learner picked that answer.
**Otherwise**             Any answer.
========================  =========================================================

Quiz conditions can only be used on quizzes, and answer conditions only on decision points.

When Rules Do Not Apply
~~~~~~~~~~~~~~~~~~~~~~~

Rules route a learner by a *result*: the first submission of a quiz, or the answer to a decision
point. Without one, the rules are ignored and the learner continues on their current path:

- **When a deadline passes without a result.** The content's usual deadline behaviour applies, and
  the learner is not routed.
- **When the content is unpublished.** Unpublished content is never sent, so it never produces a
  result and its rules route no one. Learners move straight on to the next content.

Quizzes as Branch Points
------------------------

A quiz with routing rules answers with a route, not a verdict. Its **first submission** decides where
the learner goes:

- There is no retry. The quiz's **limited attempts** setting is disabled while the quiz has rules,
  with a note explaining why.
- Failing does not end the enrollment. A failed result is a destination like any other, so the
  two-strikes deactivation that applies to ordinary quizzes never comes into play.
- This is the same whether the quiz is blocking or a practice quiz.

A quiz without routing rules behaves exactly as before.

Decision Points
---------------

A decision point asks learners one question, such as *"Do you want to review the basics first, or
go straight to the advanced material?"*. There is no right answer and no score: the answer a learner
picks is recorded, and the routing rules on the decision point send them wherever that answer
points.

Creating a Decision Point
~~~~~~~~~~~~~~~~~~~~~~~~~

On the course content page, click **Add Decision** and fill in:

**Title** (Required)
  Used as the email subject and as the heading of the answer page.

**Question** (Required)
  What learners are asked. Line breaks are kept.

**Answers** (Required)
  At least two, none of them empty. Use **Add answer** to add more, the arrows to reorder them, and
  **Remove answer** to remove one. Learners see the answers in this order.

**Send Delay**
  How long after the previous content the decision point is sent, in days or hours.

**Track**
  Where the decision point sits in the course, when the course has tracks.

**Deadline** / **Reminder Interval Days**
  An optional deadline in days, or — for a decision point without a deadline — a reminder email
  every *N* days until the learner answers, up to three reminders.

Click **Save Decision**. Once saved, the decision point's **Branching** tab is where you add rules
such as **Answered** *"Advanced"* → **Advanced track**.

.. SCREENSHOT PLACEHOLDER
   File: docs/images/add-decision-form.png
   Show: the New Decision form with a question and three answers.

Editing Answers
~~~~~~~~~~~~~~~

Changing an answer's text or position keeps the rules that match it. Removing an answer also removes
the rules that match it. An answer that a learner has already picked cannot be removed, so the record
of what learners chose stays true — edit its text instead.

What Learners Receive
~~~~~~~~~~~~~~~~~~~~~

The decision point arrives as an email showing the question, with a button that opens a page listing
the answers. The learner picks one and submits it.

- **The first answer is final.** It is recorded, and the link stops working — opening it again says
  the question has already been answered.
- **Nothing after the decision point is sent until the learner answers.** The answer decides which
  content comes next.
- **With no rules**, the answer is still recorded and the learner continues to the next content.
- **A missed deadline never ends the enrollment.** Since there is no wrong answer to fail on, the
  learner moves on to the next content on their current path, without being routed.

When AMP emails are enabled (``AMP_ENABLED``), the email can also be answered directly inside
supporting mail clients such as Gmail: the answers appear as a form in the email itself, and
submitting it works exactly like the answer page. If the answer is refused — because it was already
given on the page, for example — the email shows why and links to the page. Gmail only renders AMP
emails from sending domains
`registered with Google <https://developers.google.com/workspace/gmail/ampemail/register>`_.

.. SCREENSHOT PLACEHOLDER
   File: docs/images/decision-email.png
   Show: the decision point email as a learner receives it, with the question and the Answer button.

.. SCREENSHOT PLACEHOLDER
   File: docs/images/decision-answer-page.png
   Show: the answer page with the question, the answers as radio buttons, and the Submit button.

The Flow View
-------------

Once a course has at least one track, the course content page shows a **Table / Flow** toggle. The
Flow view draws the whole course as a diagram, so you can check where every rule sends learners at a
glance. It is read-only: build and edit the course in the table.

.. SCREENSHOT PLACEHOLDER
   File: docs/images/course-flow-view.png
   Show: the Flow view with a branch point, a labelled route onto a track, a track box, the
   dashed rejoin arrow, and the Course complete node.

Reading the Flow View
~~~~~~~~~~~~~~~~~~~~~

**Content**
  Every content is a box. The main path runs straight down the left; each track is a tinted box
  around its content, drawn beside the main path and nested inside the box of the track it branches
  off. Anything outside every track box is on the main path.

**Arrows**
  Every move a learner can make is an arrow:

  - down the path to the next content;
  - onto a track, labelled with the rule that selects it (**If failed**, **If score ≥ 80**,
    **If answered "Advanced"**);
  - dashed, from the end of a track back to where it rejoins, or on to **Course complete**.

**A branch point's next step**
  Drawn too, because learners whose result no rule matches take it. It is labelled **Otherwise**
  when no rule catches every result. Behind an **Otherwise** rule it is dashed and labelled
  **If not submitted**, since only a missing result — a deadline passing — takes it then.

**Unpublished content**
  Faded, with a dashed border and a **Not published** label. The routes out of an unpublished branch
  point are dotted, because no one takes them; its next step is drawn solid, because every learner
  does.

**Tracks no rule reaches**
  Flagged with **No rule routes here**.

Click a content box to open it, as you would a row in the table. Admins and editors can also click a
track's name to edit the track.

Learners on a Branching Course
------------------------------

Path Taken
~~~~~~~~~~

On the **Learners** page, the enrollment view of a branching course includes **Path taken**: every
content the learner has been sent or is scheduled to receive, in order, grouped by the track it is on
and marked **Sent**, **Scheduled** or **Not sent**.

.. SCREENSHOT PLACEHOLDER
   File: docs/images/learner-path-taken.png
   Show: the enrollment view of a learner who was routed onto a track, with the Path taken section.

Progress
~~~~~~~~

A percentage only means "how much of the course is behind you" while every learner walks the same
content, so progress is reported differently once a course branches:

**Progress shown to learners**
  Not shown at all on a course that has any routing rule — for every learner, including those who
  happen to take the straight line through it. A course with tracks but no rules yet is still a
  single sequence and shows progress as usual.

**Progress shown on the platform**
  Measured against the learner's own route: the content they have been sent, out of that plus the
  content still ahead of them from where they stand, assuming they are not routed again. A learner
  who finishes the course reaches 100% even though their route skipped some content.

  Because a learner's route can change length, this number can go **down**: a learner at 71% who is
  routed onto a longer remedial track might drop to 56%. Two learners on the same course can be
  measured against different totals, which is worth remembering when reading an average.

Track Analytics
~~~~~~~~~~~~~~~

The course's **Analytics** tab includes a **Tracks** table with a row for each track:

**Routed onto it**
  Learners who were sent content on the track.

**Finished**
  Learners who were then sent content outside the track, or completed the course.

**Still on it**
  Learners on the track who have not finished it yet.

**Left the course**
  Learners whose enrollment was deactivated before they finished the track.

Content on a track nested inside counts as the same track, since a learner who branches again is still
on it. The table is not shown for a course without tracks.

.. SCREENSHOT PLACEHOLDER
   File: docs/images/track-analytics.png
   Show: the Tracks table on a course's Analytics tab.

API Reference
-------------

Everything above is also available over the platform API, under
``/api/platform/organizations/<organization_id>/courses/<course_id>/``. All endpoints can be read by
every organization role and changed by admins and editors. A change the course's structure does not
allow is refused and nothing is saved: the track and routing-rule endpoints answer ``400`` with a list
of messages, and moving or reordering content answers ``409``.

**Tracks**
  - ``GET tracks/`` lists the course's tracks.
  - ``POST tracks/`` creates one: ``{"name": ..., "parent_track_id": ..., "merge_into_id": ...}``.
    Leave ``parent_track_id`` empty for a track off the main path, and ``merge_into_id`` empty for a
    track that ends the course.
  - ``POST tracks/<track_id>/`` updates a track; a field sent as ``null`` is cleared.
  - ``DELETE tracks/<track_id>/`` deletes an empty track, or returns ``409`` while it holds content.

**Routing rules**
  - ``GET contents/<content_id>/transitions/`` lists the rules on a content, in order.
  - ``PUT contents/<content_id>/transitions/`` replaces the whole set in one transaction:

    .. code-block:: json

        {
          "transitions": [
            {"condition": "score_gte", "threshold": 90, "target_id": 8},
            {"condition": "failed", "target_id": 7},
            {"condition": "default", "target_id": 9}
          ]
        }

    ``condition`` is one of ``passed``, ``failed``, ``score_gte``, ``score_lt``, ``option_selected``
    or ``default``. Score conditions take a ``threshold``; ``option_selected`` takes the ``option_id``
    of an answer of the same decision point.

  - ``POST contents/<content_id>/transitions/`` adds a single rule with an explicit ``order``, and
    ``DELETE contents/<content_id>/transitions/<transition_id>/`` removes one.

**Course content**
  - ``GET contents/`` returns the course's ``course_contents`` together with its ``tracks`` and
    ``transitions``, and each content carries its ``track_id``.
  - ``POST contents/`` and ``POST contents/<content_id>/`` accept ``track_id``; ``null`` means the main
    path.
  - A decision point is created with ``{"type": "decision", "title": ..., "prompt": ...,
    "options": [{"text": ...}, ...]}`` as its ``content``. An update takes the full list of answers in
    order: answers with an ``id`` are edited, those without are added, and those left out are removed.
    Removing an answer a learner has already picked returns ``409``.

**Track analytics**
  - ``GET /api/analytics/organizations/<organization_id>/track-breakdown/?course_id=<course_id>``
    returns the numbers behind the **Tracks** table.
