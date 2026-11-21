export class Carousel {
    example: JQuery<HTMLElement>;
    views: JQuery<HTMLElement>;
    images: string[] = [];

    constructor(example: JQuery<HTMLElement>, views: JQuery<HTMLElement>) {
        this.example = example;
        this.views = views;
    }

    init() {
    }

    update() {
        this.views.empty();
        this.images.forEach((image) => {
            this.views.append(`<li><a><img src="${image}" /></a></li>`);
        });
        this.views.find("img").on("click", (event) => {
            event.preventDefault();
            const image_src = $(event.target).attr("src");
            if (image_src) {
                this.example.attr("src", image_src);
            }
        });
        this.example.attr("src", this.images[0]);
    }
}
