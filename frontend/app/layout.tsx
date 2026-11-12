import type { Metadata } from 'next';
import './globals.css';
import './polish.css';
export const metadata: Metadata = {title:'BiteAI · Find your next favourite',description:'Mumbai food discovery, thoughtfully matched to your craving.'};
export default function RootLayout({children}:{children:React.ReactNode}) {
  return <html lang="en"><body>{children}</body></html>;
}
