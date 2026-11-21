export class Carousel {
    example: JQuery<HTMLElement>;
    views: JQuery<HTMLElement>;
    images: string[] = [];

    constructor(example: JQuery<HTMLElement>, views: JQuery<HTMLElement>) {
        this.example = example;
        this.views = views;
    }

    init() {
        // TODO: This code really has to happen after thumbnail images are added, but we're testing now with static HTML
        this.views.find("img").on("click", (event) => {
            event.preventDefault();
            const image_src = $(event.target).attr("src");
            console.log("Image src: ", image_src);
            if (image_src) {
                this.example.attr("src", image_src);
                console.log("Image src set");
            }
        });
    }
}
