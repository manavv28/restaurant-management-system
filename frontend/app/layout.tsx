import type { Metadata } from 'next';
import './globals.css';
import './polish.css';
import './concierge.css';
import './audit.css';
export const metadata: Metadata = {title:'BiteAI · Find your next favourite',description:'Mumbai food discovery, thoughtfully matched to your craving.'};
export default function RootLayout({children}:{children:React.ReactNode}) {
  return <html lang="en" data-theme="night" suppressHydrationWarning><body>{children}</body></html>;
}
