"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

const HERO_IMAGES = [
  "/images/hero/hero-001.png",
  "/images/hero/hero-002.jpg",
  "/images/hero/hero-003.jpg",
  "/images/hero/hero-004.webp",
] as const;

export function HeroCarousel() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const id = window.setInterval(() => {
      setIndex((current) => (current + 1) % HERO_IMAGES.length);
    }, 10_000);

    return () => window.clearInterval(id);
  }, []);

  return (
    <div aria-hidden="true" className="hero-carousel">
      <div
        className="hero-carousel-track"
        style={{ transform: `translateX(-${index * 100}%)` }}
      >
        {HERO_IMAGES.map((src, slideIndex) => (
          <div key={src} className="hero-carousel-slide relative">
            <Image
              src={src}
              alt=""
              fill
              sizes="100vw"
              priority={slideIndex === 0}
              className={
                src.includes("hero-002")
                  ? "hero-carousel-image hero-carousel-image--top"
                  : "hero-carousel-image"
              }
            />
          </div>
        ))}
      </div>
    </div>
  );
}
