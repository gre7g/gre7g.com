import { $ } from "jquery";

/**
 * The product image carousel on the product listing page.
 *
 * Shows a large example image (#example) with a list of thumbnails (#views) beside it. Clicking a thumbnail shows
 * that image as the example.
 */
export class Carousel {
    // Large image element
    example: JQuery<HTMLElement>;
    // <ul> that holds the thumbnails
    views: JQuery<HTMLElement>;
    // Image URLs to show; set before calling update()
    images: string[] = [];

    constructor(example: JQuery<HTMLElement>, views: JQuery<HTMLElement>) {
        this.example = example;
        this.views = views;
    }

    /**
     * One-time setup. Nothing to do yet.
     */
    init() {
    }

    /**
     * Rebuild the thumbnails from images and show the first image as the example.
     */
    update() {
        this.views.empty();
        this.images.forEach((image) => {
            this.views.append(`<li><a><img src="${image}" /></a></li>`);
        });
        // Handlers are attached to the new <img> elements, so they're replaced along with the thumbnails
        this.views.find("img").on("click", (event) => {
            event.preventDefault();
            const image_src = $(event.target).attr("src");
            if (image_src) {
                this.example.attr("src", image_src);
            }
        });
        this.example.attr("src", this.images[0]);
        this.views.toggle(this.images.length > 1);
    }
}
