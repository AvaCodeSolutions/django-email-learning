import { describe, it, expect } from 'vitest';
import { slugify } from '../utils.js';

describe('slugify', () => {
  it('lowercases and hyphenates spaces', () => {
    expect(slugify('My Great Course')).toBe('my-great-course');
  });

  it('strips punctuation', () => {
    expect(slugify('Intro to Django: The Basics!')).toBe('intro-to-django-the-basics');
  });

  it('collapses repeated separators and trims leading/trailing hyphens', () => {
    expect(slugify('  --Weird   Title--  ')).toBe('weird-title');
  });

  it('truncates to 50 characters', () => {
    const longTitle = 'a'.repeat(80);
    expect(slugify(longTitle)).toHaveLength(50);
  });
});
