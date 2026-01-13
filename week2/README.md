# Day 1 

So basically today was all about understanding the skeleton of a webpage. We didn't touch CSS, just pure structure. here is what i learnt.

What i learnt today

## 1. Page Structure

What it is: The standard frame we use for every website. **!DOCTYPE html**, **html**, **head**, **body**.

Why we use it: To tell the browser we are using modern html5 (Standard Mode) and not the old "Quirks Mode".

How: Just type ! and enter in VS code usually, but good to know what goes where.

## 2. Semantic HTML

What it is: Using tags that actually mean something like **header** which contains the info at the top of the section, **nav** which contains links for navigation, **article** which is used to contain independent information like a... article , **aside** it's content is vertically opposite to the main parts like article, for eg in the right and it contains data indirectly related to the documents main content. it tells the browser that it is not the main focus of the page, etc. instead of just using **div** everywhere.

Why we need this:

For developers so we kow where what is, and don't spend our time on finding these things.

For Screen Readers. The browser forms a structure called the accessiblity tree which can be used by blind people to navigate through the web page using shortcuts.

For SEO so that the website can rank higher. The google bots look for these tags, instead of divs

Note: Without css, these tags look exactly like divs. The difference is in the functionality.

## 3. Accessibility (ARIA & Alt)

Alt Text: Text description for images. crucial if image breaks or for blind users.

ARIA labels: they are like instructions for screen readers. we mainly use it on buttons that can just be items. mainly for diffrently abled.

Screen Readers: Tools that read the site out loud. They rely on our semantic tags to navigate.

## 4. Forms

Select: Used a dropdown menu for categories.

Validation: Added required and minlength="3" to the search box.

Why: So users dont crash the server by sending empty search queries.

## The Project: Martial Blog

Built a blog.html page for "Martial Blog".

Used **header** for the logo and main menu.

Used **main** for the actual blog content.

Used **section** to divide things like "Hero", "Newsletter", and "Feed".

Used **article** for the individual blog posts so they are self-contained.

Used **aside** for the sidebar (search, tags, etc) because its parallel to the main content.

