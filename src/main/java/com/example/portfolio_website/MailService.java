package com.example.portfolio_website;

import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

@Service
public class MailService {
    private final ContactMessageRepository repository;

    public MailService(ContactMessageRepository repository) {
        this.repository = repository;
    }

    public void save(ContactRequest request) {

        ContactMessage message = new ContactMessage();

        message.setName(request.getName());
        message.setEmail(request.getEmail());
        message.setMessage(request.getMessage());
        message.setCreatedAt(LocalDateTime.now());

        repository.save(message);
    }
}
