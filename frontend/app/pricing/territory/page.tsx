import type { Metadata } from "next";
import Link from "next/link";
import { Inter, Source_Serif_4 } from "next/font/google";

import TerritoryScopePicker from "@/components/TerritoryScopePicker";
import { CQC_INDEPENDENCE_LINE } from "@/lib/caregist-config";
import { TERRITORY_BRIEF_PRICE_GBP } from "@/lib/territory-scope";

import styles from "./territory.module.css";

// Scoped to this route only — see DESIGN.md: adopting these fonts sitewide is
// a separate, reviewed decision, not a side effect of polishing one page.
const territorySerif = Source_Serif_4({
  subsets: ["latin"],
  weight: ["600"],
  variable: "--font-territory-serif",
  display: "swap",
});
const territoryInter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-territory-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Confirm your territory | CareGist Territory Opportunity Brief",
  description:
    "Check coverage for your territory and review the next steps for a Territory Opportunity Brief.",
};

export default function TerritoryScopePage() {
  return (
    <main className={`${styles.wrap} ${territorySerif.variable} ${territoryInter.variable}`}>
      <header className={styles.top}>
        <Link href="/pricing" className={styles.back}>
          ← Back to pricing
        </Link>
        <div className={styles.brand}>
          CareGist <span className={styles.kicker}>Territory intelligence</span>
        </div>
      </header>

      <section className={styles.hero}>
        <div>
          <div className={styles.kicker}>One-off Territory Opportunity Brief</div>
          <h1>Know which care organisations to research first.</h1>
          <p className={styles.intro}>
            A territory-specific account review for UK care-sector suppliers and advisers.
            Get a shortlist built against your agreed criteria, with the source facts and
            limits visible throughout.
          </p>
        </div>
        <aside className={styles.priceBox}>
          <div className={styles.kicker}>Territory Opportunity Brief</div>
          <div className={styles.price}>£{TERRITORY_BRIEF_PRICE_GBP}</div>
          <p className={styles.vat}>£745 is the final price. H-Kay Limited is not VAT registered, so no VAT is added.</p>
          <a href="#check-coverage" className={styles.button}>
            Check your territory
          </a>
          <p className={styles.note}>
            <strong>Online ordering is not available.</strong> Check coverage and email your
            scope for review. No payment is taken on this page, and a coverage count does not
            confirm pack availability or delivery.
          </p>
        </aside>
      </section>

      <hr className={styles.rule} />

      <section className={styles.section}>
        <div className={styles.kicker}>What you receive</div>
        <h2>A clear account-research starting point</h2>
        <p className={styles.sectionLead}>
          The Brief is designed for a defined territory and question. It gives your team a
          reusable account list and a transparent reason to review each selected organisation.
        </p>
        <div className={styles.grid}>
          <article className={styles.card}>
            <div className={styles.num}>01</div>
            <h3>Territory dataset</h3>
            <p>
              An editable CSV and Excel workbook of qualifying care locations in the agreed
              scope, with provider grouping and source fields.
            </p>
          </article>
          <article className={styles.card}>
            <div className={styles.num}>02</div>
            <h3>25–50 organisations</h3>
            <p>
              A shortlist selected against your agreed criteria. Every entry carries a
              published fact, reason for inclusion, qualification question and stated
              uncertainty.
            </p>
          </article>
          <article className={styles.card}>
            <div className={styles.num}>03</div>
            <h3>Executive brief</h3>
            <p>
              A three to five page summary of the territory, priorities, evidence and limits
              so your team can decide what to check next.
            </p>
          </article>
          <article className={styles.card}>
            <div className={styles.num}>04</div>
            <h3>Traceable evidence</h3>
            <p>
              Source edition dates, location and provider identifiers, and links to published
              CQC evidence where retained in the delivery pack.
            </p>
          </article>
        </div>
      </section>

      <section className={styles.section} id="check-coverage">
        <div className={styles.kicker}>Check coverage first</div>
        <h2>See how many organisations match your scope</h2>
        <p className={styles.sectionLead}>
          Pick a region and buyer type below. We check the published CQC record for that exact
          scope before you email us — this is free, and it does not place an order.
        </p>
        <TerritoryScopePicker />
      </section>

      <section className={styles.section}>
        <div className={styles.kicker}>How it works</div>
        <h2>Agree the question, then build the Brief</h2>
        <div className={styles.grid} style={{ marginTop: 25 }}>
          <article className={styles.card}>
            <div className={styles.num}>STEP 1</div>
            <h3>Check coverage</h3>
            <p>
              Use the tool above to see how many organisations match your region and buyer
              type, then email us your scope.
            </p>
          </article>
          <article className={styles.card}>
            <div className={styles.num}>STEP 2</div>
            <h3>Source and delivery check</h3>
            <p>
              CareGist confirms that the available public source supports the scope, then
              agrees the actual delivery date.
            </p>
          </article>
          <article className={styles.card}>
            <div className={styles.num}>STEP 3</div>
            <h3>Delivery</h3>
            <p>
              The documented target is three working days after scope and source checks. The
              confirmed date is recorded before work starts.
            </p>
          </article>
          <article className={styles.card}>
            <div className={styles.num}>STEP 4</div>
            <h3>Use the shortlist</h3>
            <p>
              Review the evidence, map the fields to your CRM and qualify accounts through your
              own sales or advisory process.
            </p>
          </article>
        </div>
      </section>

      <section className={styles.limits}>
        <div>
          <div className={styles.kicker}>What it is</div>
          <p>
            A dated, evidence-led account-research pack. It helps organise published
            care-sector information around your question.
          </p>
        </div>
        <div>
          <div className={styles.kicker}>What it is not</div>
          <p>
            It does not establish vacancies, budgets, buying intent, current compliance,
            ownership, director links or a guaranteed commercial outcome.
          </p>
        </div>
      </section>

      <footer className={styles.footer}>
        <p>
          CareGist is independent of the Care Quality Commission and does not represent or
          endorse it. CQC information is reused under the Open Government Licence v3.0.{" "}
          {CQC_INDEPENDENCE_LINE}
        </p>
        <p style={{ marginTop: 8 }}>
          Prefer to talk it through first?{" "}
          <Link href="/pricing">See all products</Link> or email{" "}
          <a href="mailto:outreach@caregist.co.uk">outreach@caregist.co.uk</a>.
        </p>
      </footer>
    </main>
  );
}
