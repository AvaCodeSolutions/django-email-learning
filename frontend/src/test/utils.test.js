import { describe, it, expect } from 'vitest';
import { slugify, getReadableTextColor, getComplementaryColor } from '../utils.js';

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

describe('getReadableTextColor', () => {
  it('returns white text for dark backgrounds', () => {
    expect(getReadableTextColor('#000000')).toBe('#ffffff');
    expect(getReadableTextColor('#232936')).toBe('#ffffff');
    expect(getReadableTextColor('#4A5EC0')).toBe('#ffffff');
  });

  it('returns dark text for light backgrounds', () => {
    expect(getReadableTextColor('#ffffff')).toBe('#232936');
    expect(getReadableTextColor('#f8f8fb')).toBe('#232936');
    expect(getReadableTextColor('#EDFAF6')).toBe('#232936');
  });

  it('supports 3-digit hex shorthand', () => {
    expect(getReadableTextColor('#000')).toBe('#ffffff');
    expect(getReadableTextColor('#fff')).toBe('#232936');
  });

  it('falls back to white text for invalid or missing input', () => {
    expect(getReadableTextColor('')).toBe('#ffffff');
    expect(getReadableTextColor(null)).toBe('#ffffff');
    expect(getReadableTextColor('not-a-color')).toBe('#ffffff');
  });

  it('accepts custom dark/light overrides', () => {
    expect(getReadableTextColor('#ffffff', '#111111', '#eeeeee')).toBe('#111111');
    expect(getReadableTextColor('#000000', '#111111', '#eeeeee')).toBe('#eeeeee');
  });
});
