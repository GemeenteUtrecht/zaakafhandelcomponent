export interface LandingPage {
  title: string,
  image: string,
  sections: [
    {
      name: string,
      icon: string,
      links: [
        {
          icon: string,
          label: string,
          href: string
        }
      ]
    }
  ],
  links: [
    {
      icon: string,
      label: string,
      href: string
    }
  ]
}
