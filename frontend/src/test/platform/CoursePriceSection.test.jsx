import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import CoursePriceSection from '../../../platform/courses/components/CoursePriceSection';
import {
  EMPTY_PRICE_SETTINGS,
  priceSettingsFrom,
  priceUpdate,
  validatePriceSettings,
} from '../../../platform/courses/components/coursePrice';

const localeMessages = {
  course_price: 'Price',
  course_price_currency: 'Currency',
  course_price_subtitle: 'Price subtitle',
  course_price_invalid: 'Invalid price',
  course_price_currency_required: 'Currency required',
  course_price_requires_amount: 'Price required',
};

describe('validatePriceSettings', () => {
  it('accepts no price at all', () => {
    expect(validatePriceSettings(EMPTY_PRICE_SETTINGS, localeMessages)).toEqual({});
  });

  it.each(['10', '10.5', '10.55', '0', '12345678.99'])('accepts %s', (price) => {
    expect(validatePriceSettings({ price, currency: 'USD', subtitle: '' }, localeMessages)).toEqual({});
  });

  it.each(['10.555', '-1', 'abc', '10.', '123456789'])('rejects %s', (price) => {
    expect(validatePriceSettings({ price, currency: 'USD', subtitle: '' }, localeMessages).price).toBe('Invalid price');
  });

  it('requires a currency with a price', () => {
    expect(validatePriceSettings({ price: '10', currency: '', subtitle: '' }, localeMessages).currency)
      .toBe('Currency required');
  });

  it('requires a price with a subtitle', () => {
    expect(validatePriceSettings({ price: '', currency: '', subtitle: 'Paid' }, localeMessages).price)
      .toBe('Price required');
  });
});

describe('priceUpdate', () => {
  const initial = priceSettingsFrom({ price: '10.00', price_currency: 'USD', price_subtitle: 'Paid' });

  it('sends nothing when nothing changed', () => {
    expect(priceUpdate(initial, initial)).toEqual({});
  });

  it('sends only the changed fields', () => {
    expect(priceUpdate({ ...initial, price: '12.50' }, initial)).toEqual({ price: '12.50' });
  });

  it('clears emptied fields with null', () => {
    expect(priceUpdate(EMPTY_PRICE_SETTINGS, initial)).toEqual({
      price: null,
      price_currency: null,
      price_subtitle: null,
    });
  });
});

describe('CoursePriceSection', () => {
  it('turns a decimal comma into a point', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(
      <CoursePriceSection value={EMPTY_PRICE_SETTINGS} onChange={onChange} localeMessages={localeMessages} />
    );

    await user.type(screen.getByLabelText('Price'), ',');

    expect(onChange).toHaveBeenLastCalledWith({ ...EMPTY_PRICE_SETTINGS, price: '.' });
  });

  it('shows the selected currency', () => {
    renderWithProviders(
      <CoursePriceSection
        value={{ price: '10', currency: 'EUR', subtitle: '' }}
        onChange={vi.fn()}
        localeMessages={localeMessages}
      />
    );

    expect(screen.getByLabelText('Currency').value).toMatch(/^EUR - /);
  });
});
