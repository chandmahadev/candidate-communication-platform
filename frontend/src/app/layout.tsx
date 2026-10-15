import type { Metadata } from "next";
import { Lato } from "next/font/google";
import { AppProviders } from "@/components/providers/AppProviders";
import "./globals.css";

const lato = Lato({
  variable: "--font-lato",
  weight: ["400", "700"],
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Candidate communication",
  description: "Manage candidates, send messages and track delivery.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={lato.variable}>
      <body>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
