import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Venmo',
  description: 'P2P payment platform',
};

export default function RootLayout({ children }: { children: React.ReactNode }): React.ReactElement {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
