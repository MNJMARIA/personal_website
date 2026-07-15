package com.example.portfolio_website;

import org.springframework.data.jpa.repository.JpaRepository;

public interface ContactMessageRepository
        extends JpaRepository<ContactMessage, Long> {

}
