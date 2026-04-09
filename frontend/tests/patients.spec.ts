import { expect, test } from "@playwright/test"
import { createUser } from "./utils/privateApi"
import {
  randomEmail,
  randomPatientDescription,
  randomPatientTitle,
  randomPassword,
} from "./utils/random"
import { logInUser } from "./utils/user"

test("Patients page is accessible and shows correct title", async ({ page }) => {
  await page.goto("/patients")
  await expect(page.getByRole("heading", { name: "Patients" })).toBeVisible()
  await expect(page.getByText("Create and manage patients")).toBeVisible()
})

test("Add Patient button is visible", async ({ page }) => {
  await page.goto("/patients")
  await expect(page.getByRole("button", { name: "Add Patient" })).toBeVisible()
})

test.describe("Patients management", () => {
  test.use({ storageState: { cookies: [], origins: [] } })
  let email: string
  const password = randomPassword()

  test.beforeAll(async () => {
    email = randomEmail()
    await createUser({ email, password })
  })

  test.beforeEach(async ({ page }) => {
    await logInUser(page, email, password)
    await page.goto("/patients")
  })

  test("Create a new patient successfully", async ({ page }) => {
    const title = randomPatientTitle()
    const description = randomPatientDescription()

    await page.getByRole("button", { name: "Add Patient" }).click()
    await page.getByLabel("Title").fill(title)
    await page.getByLabel("Description").fill(description)
    await page.getByRole("button", { name: "Save" }).click()

    await expect(page.getByText("Patient created successfully")).toBeVisible()
    await expect(page.getByText(title)).toBeVisible()
  })

  test("Create patient with only required fields", async ({ page }) => {
    const title = randomPatientTitle()

    await page.getByRole("button", { name: "Add Patient" }).click()
    await page.getByLabel("Title").fill(title)
    await page.getByRole("button", { name: "Save" }).click()

    await expect(page.getByText("Patient created successfully")).toBeVisible()
    await expect(page.getByText(title)).toBeVisible()
  })

  test("Cancel patient creation", async ({ page }) => {
    await page.getByRole("button", { name: "Add Patient" }).click()
    await page.getByLabel("Title").fill("Test Patient")
    await page.getByRole("button", { name: "Cancel" }).click()

    await expect(page.getByRole("dialog")).not.toBeVisible()
  })

  test("Title is required", async ({ page }) => {
    await page.getByRole("button", { name: "Add Patient" }).click()
    await page.getByLabel("Title").fill("")
    await page.getByLabel("Title").blur()

    await expect(page.getByText("Title is required")).toBeVisible()
  })

  test.describe("Edit and Delete", () => {
    let patientTitle: string

    test.beforeEach(async ({ page }) => {
      patientTitle = randomPatientTitle()

      await page.getByRole("button", { name: "Add Patient" }).click()
      await page.getByLabel("Title").fill(patientTitle)
      await page.getByRole("button", { name: "Save" }).click()
      await expect(page.getByText("Patient created successfully")).toBeVisible()
      await expect(page.getByRole("dialog")).not.toBeVisible()
    })

    test("Edit a patient successfully", async ({ page }) => {
      const patientRow = page.getByRole("row").filter({ hasText: patientTitle })
      await patientRow.getByRole("button").last().click()
      await page.getByRole("menuitem", { name: "Edit Patient" }).click()

      const updatedTitle = randomPatientTitle()
      await page.getByLabel("Title").fill(updatedTitle)
      await page.getByRole("button", { name: "Save" }).click()

      await expect(page.getByText("Patient updated successfully")).toBeVisible()
      await expect(page.getByText(updatedTitle)).toBeVisible()
    })

    test("Delete a patient successfully", async ({ page }) => {
      const patientRow = page.getByRole("row").filter({ hasText: patientTitle })
      await patientRow.getByRole("button").last().click()
      await page.getByRole("menuitem", { name: "Delete Patient" }).click()

      await page.getByRole("button", { name: "Delete" }).click()

      await expect(
        page.getByText("The patient was deleted successfully"),
      ).toBeVisible()
      await expect(page.getByText(patientTitle)).not.toBeVisible()
    })
  })
})

test.describe("Patients empty state", () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test("Shows empty state message when no patients exist", async ({ page }) => {
    const email = randomEmail()
    const password = randomPassword()
    await createUser({ email, password })
    await logInUser(page, email, password)

    await page.goto("/patients")

    await expect(page.getByText("No patients found")).toBeVisible()
    await expect(page.getByText("No patients have been assigned to you yet")).toBeVisible()
  })
})
