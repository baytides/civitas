import type { GlobalConfig } from "payload";

export const SiteSettings: GlobalConfig = {
  slug: "site-settings",
  admin: {
    group: "Admin",
  },
  access: {
    read: () => true,
    update: ({ req: { user } }) => user?.role === "admin",
  },
  fields: [
    {
      name: "siteTitle",
      type: "text",
      required: true,
      defaultValue: "Civitas",
    },
    {
      name: "tagline",
      type: "text",
      defaultValue: "Protecting American Democracy",
    },
    {
      name: "threatLevel",
      type: "group",
      fields: [
        {
          name: "level",
          type: "select",
          options: [
            { label: "Critical", value: "critical" },
            { label: "High", value: "high" },
            { label: "Elevated", value: "elevated" },
            { label: "Moderate", value: "moderate" },
          ],
          defaultValue: "elevated",
        },
        {
          name: "autoCalculate",
          type: "checkbox",
          defaultValue: true,
          admin: {
            description: "Automatically calculate from implementation progress",
          },
        },
        {
          name: "manualOverrideReason",
          type: "text",
          admin: {
            condition: (data) => !data?.threatLevel?.autoCalculate,
          },
        },
      ],
    },
    {
      name: "featuredObjectiveIds",
      type: "json",
      admin: {
        description: "Array of P2025 objective IDs to feature on homepage",
      },
    },
    {
      name: "navigation",
      type: "array",
      fields: [
        {
          name: "label",
          type: "text",
          required: true,
        },
        {
          name: "url",
          type: "text",
          required: true,
        },
        {
          name: "external",
          type: "checkbox",
          defaultValue: false,
        },
      ],
    },
    {
      name: "footer",
      type: "group",
      fields: [
        {
          name: "copyrightText",
          type: "text",
          defaultValue: "Project Civitas",
        },
        {
          name: "links",
          type: "array",
          fields: [
            {
              name: "label",
              type: "text",
              required: true,
            },
            {
              name: "url",
              type: "text",
              required: true,
            },
          ],
        },
      ],
    },
  ],
};
