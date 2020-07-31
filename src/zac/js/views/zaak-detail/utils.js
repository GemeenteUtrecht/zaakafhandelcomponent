const getAuthorName = (author) => {
    return author.last_name ? `${author.first_name} ${author.last_name}` : author.username;
};


export { getAuthorName };
