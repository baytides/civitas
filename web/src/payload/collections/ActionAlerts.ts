import type { CollectionConfig } from "payload";

export const ActionAlerts: CollectionConfig = {
  slug: "action-alerts",
  admin: {
    useAsTitle: "title",
    defaultColumns: ["title", "urgency", "expiresAt", "active"],
    group: "Content",
  },
  access: {
    read: () => true,
    create: ({ req: { user } }) => !!user,
    update: ({ req: { user } }) => !!user,
    delete: ({ req: { user } }) => user?.role === "admin",
  },
  fields: [
    {
      name: "title",
      type: "text",
      required: true,
    },
    {
      name: "urgency",
      type: "select",
      required: true,
      defaultValue: "medium",
      options: [
        { label: "Critical", value: "critical" },
        { label: "High", value: "high" },
        { label: "Medium", value: "medium" },
      ],
      admin: {
        position: "sidebar",
      },
    },
    {
      name: "description",
      type: "richText",
      required: true,
    },
    {
      name: "callToAction",
      type: "group",
      fields: [
        {
          name: "text",
          type: "text",
          required: true,
          defaultValue: "Take Action",
        },
        {
          name: "url",
          type: "text",
          required: true,
        },
      ],
    },
    {
      name: "relatedObjectiveIds",
      type: "json",
      admin: {
        description: "Array of P2025 objective IDs this alert relates to",
      },
    },
    {
      name: "displayLocations",
      type: "select",
      hasMany: true,
      options: [
        { label: "Homepage", value: "homepage" },
        { label: "Tracker", value: "tracker" },
        { label: "Category Pages", value: "category" },
      ],
      defaultValue: ["homepage"],
    },
    {
      name: "active",
      type: "checkbox",
      defaultValue: true,
      admin: {
        position: "sidebar",
      },
    },
    {
      name: "expiresAt",
      type: "date",
      admin: {
        position: "sidebar",
        date: {
          pickerAppearance: "dayAndTime",
        },
      },
    },
  ],
};
