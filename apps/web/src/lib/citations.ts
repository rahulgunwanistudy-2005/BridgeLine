export function cornellCitationUrl(citation: string): string {
  const section = /§(\d+\.\d+)/.exec(citation)?.[1];
  return section === undefined
    ? "https://www.law.cornell.edu/cfr/text/34/part-300"
    : `https://www.law.cornell.edu/cfr/text/34/${section}`;
}
