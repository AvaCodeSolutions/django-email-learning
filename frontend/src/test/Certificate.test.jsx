import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import { Certificate } from '../../personalised/certificate/Certificate.jsx';

vi.mock('../render.jsx');

const defaultAppContext = {
    name: 'Jane Doe',
    issueDate: 'January 01, 2025',
    certificateNumber: 'ORG-COURSE-42-abc123',
    qrcodeUrl: 'https://example.com/qr.png',
    logoUrl: 'https://example.com/logo.png',
    localeMessages: {
        title: 'Certificate of Completion',
        description: 'This certifies that Jane Doe has successfully completed the React Fundamentals course',
        issue_date: 'Issued on',
        certificate_number: 'Certificate Number',
        organization_team: 'Acme Team',
    },
};

describe('Certificate', () => {
    it('renders the certificate title', () => {
        renderWithProviders(<Certificate />, { appContext: defaultAppContext });
        expect(screen.getByText('Certificate of Completion')).toBeInTheDocument();
    });

    it('renders the recipient name in the description', () => {
        renderWithProviders(<Certificate />, { appContext: defaultAppContext });
        expect(screen.getByText(/Jane Doe/)).toBeInTheDocument();
    });

    it('renders the issue date', () => {
        renderWithProviders(<Certificate />, { appContext: defaultAppContext });
        expect(screen.getByText(/Issued on/)).toBeInTheDocument();
        expect(screen.getByText(/January 01, 2025/)).toBeInTheDocument();
    });

    it('renders the certificate number', () => {
        renderWithProviders(<Certificate />, { appContext: defaultAppContext });
        expect(screen.getByText(/Certificate Number/)).toBeInTheDocument();
        expect(screen.getByText(/ORG-COURSE-42-abc123/)).toBeInTheDocument();
    });

    it('renders the organization team name', () => {
        renderWithProviders(<Certificate />, { appContext: defaultAppContext });
        expect(screen.getByText('Acme Team')).toBeInTheDocument();
    });

    it('renders the QR code image', () => {
        renderWithProviders(<Certificate />, { appContext: defaultAppContext });
        const qrImg = screen.getByAltText('QR Code');
        expect(qrImg).toBeInTheDocument();
        expect(qrImg).toHaveAttribute('src', 'https://example.com/qr.png');
    });

    it('renders the organization logo when provided', () => {
        renderWithProviders(<Certificate />, { appContext: defaultAppContext });
        const logoImg = screen.getByAltText('Organization Logo');
        expect(logoImg).toBeInTheDocument();
        expect(logoImg).toHaveAttribute('src', 'https://example.com/logo.png');
    });

    it('does not render the organization logo when logoUrl is empty', () => {
        renderWithProviders(<Certificate />, {
            appContext: { ...defaultAppContext, logoUrl: '' },
        });
        expect(screen.queryByAltText('Organization Logo')).not.toBeInTheDocument();
    });

    it('shows an error alert when errorMessage is present', () => {
        renderWithProviders(<Certificate />, {
            appContext: { ...defaultAppContext, errorMessage: 'Certificate not found' },
        });
        expect(screen.getByText('Certificate not found')).toBeInTheDocument();
        expect(screen.queryByText('Certificate of Completion')).not.toBeInTheDocument();
    });
});
