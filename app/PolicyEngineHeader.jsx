"use client";

import { Header } from "@policyengine/ui-kit";

const navItems = [
  { label: "Research", href: "https://policyengine.org/us/research" },
  { label: "Model", href: "https://policyengine.org/us/model" },
  { label: "API", href: "https://policyengine.org/us/api" },
  {
    label: "About",
    href: "https://policyengine.org/us/team",
    children: [
      { label: "Team", href: "https://policyengine.org/us/team" },
      { label: "Supporters", href: "https://policyengine.org/us/supporters" },
    ],
  },
  { label: "Donate", href: "https://policyengine.org/us/donate" },
];

const countries = [
  { id: "us", label: "United States" },
  { id: "uk", label: "United Kingdom" },
];

export default function PolicyEngineHeader() {
  return (
    <Header
      navItems={navItems}
      countries={countries}
      currentCountry="us"
      logoHref="https://policyengine.org/us"
      onCountryChange={(countryId) => {
        window.location.href = `https://policyengine.org/${countryId}`;
      }}
    />
  );
}
