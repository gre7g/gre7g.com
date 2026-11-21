export class Carousel {
    example: JQuery<HTMLElement>;
    views: JQuery<HTMLElement>;
    images: string[] = [];

    constructor(example: JQuery<HTMLElement>, views: JQuery<HTMLElement>) {
        this.example = example;
        this.views = views;
    }

    init() {}
}
