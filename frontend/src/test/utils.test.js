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

describe('getComplementaryColor', () => {
  const getContrastRatio = (hexColor) => {
    const hex = hexColor.replace('#', '');
    const r = parseInt(hex.slice(0, 2), 16) / 255;
    const g = parseInt(hex.slice(2, 4), 16) / 255;
    const b = parseInt(hex.slice(4, 6), 16) / 255;

    const toLinear = (channel) => {
      return channel <= 0.03928
        ? channel / 12.92
        : ((channel + 0.055) / 1.055) ** 2.4;
    };

    const luminance = (value) => toLinear(value);
    const l1 = 0.2126 * luminance(r) + 0.7152 * luminance(g) + 0.0722 * luminance(b);
    const l2 = 1;
    const lighter = Math.max(l1, l2);
    const darker = Math.min(l1, l2);

    return (lighter + 0.05) / (darker + 0.05);
  };

  it('returns a color with strong contrast against white text', () => {
    expect(getContrastRatio(getComplementaryColor('#ff0000'))).toBeGreaterThanOrEqual(4.5);
    expect(getContrastRatio(getComplementaryColor('#00ff00'))).toBeGreaterThanOrEqual(4.5);
    expect(getContrastRatio(getComplementaryColor('#0000ff'))).toBeGreaterThanOrEqual(4.5);
  });
});
